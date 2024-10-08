import httpx
from aiogram import types, F, Router
from aiogram.fsm.context import FSMContext

from engine import repo, middleware
from utils import texts as t
from utils.assist import get_msg_from_state, check_price, check_percent
from utils.fsm_states import CreateRequestFSM
from utils.keyboards import CreateNoticeKB, KB
from utils.models import UserRequestSchema, Price, Way, PercentOfPoint, PercentOfTime, Period
from utils.services import Requests

router = Router()
router.message.middleware(middleware)
router.callback_query.middleware(middleware)


@router.message(CreateRequestFSM.get_ticker_name)
async def cn_ask_type_notice(message: types.Message, state: FSMContext):
    await message.delete()
    msg = await get_msg_from_state(state)
    if not repo.tickers:
        await msg.edit_text('Сервис временно недоступен', reply_markup=KB.main())
    elif (message.text.upper() + 'USDT') in repo.tickers:
        current_price = await repo.get_current_price(message.text.upper() + 'USDT')
        await state.update_data({'ticker_name': f'{message.text.upper()}USDT'})
        await msg.edit_text(t.ask_type_notice(message.text, 'USDT', current_price),
                            reply_markup=CreateNoticeKB.type_notice())
        await state.set_state(CreateRequestFSM.set_type_request)
    else:
        await msg.edit_text('Такой пары не существует. Попробуйте заново.', reply_markup=KB.back_to_main())


@router.callback_query(F.data == 'cn_price_up')
async def cn_ask_price_up(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.set_state(CreateRequestFSM.get_ticker_name)
    msg = await callback.message.edit_text(
        '<b><u>Уведомление сработает при повышении цены до указанного значения.</u></b>\n\n'
        f'Текущая цена: {await repo.get_current_price(data["ticker_name"])}\n\n'
        'Введите цену:',
        reply_markup=KB.back_to_main())
    await state.update_data({'type_notice': 'price_up', 'msg': msg})
    await state.set_state(CreateRequestFSM.get_price)


@router.callback_query(F.data == 'cn_price_down')
async def cn_ask_price_down(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.set_state(CreateRequestFSM.get_ticker_name)
    msg = await callback.message.edit_text(
        '<b><u>Уведомление сработает при снижении цены до указанного значения.</u></b>\n\n'
        f'Текущая цена: {await repo.get_current_price(data["ticker_name"])}\n\n'
        'Введите цену:',
        reply_markup=KB.back_to_main())
    await state.update_data({'type_notice': 'price_down', 'msg': msg})
    await state.set_state(CreateRequestFSM.get_price)


@router.callback_query(F.data == 'cn_period_24h')
async def cn_ask_period_24h_percent(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.set_state(CreateRequestFSM.get_ticker_name)
    msg = await callback.message.edit_text(
        '<b><u>Уведомление сработает при изменении цены в % за последние 24 часа до указанного значения %.</u></b>\n\n'
        f'Текущая цена: {await repo.get_current_price(data["ticker_name"])}\n\n'
        'Введите процент:',
        reply_markup=KB.back_to_main())
    await state.update_data({'type_notice': 'period_24h', 'msg': msg})
    await state.set_state(CreateRequestFSM.get_period_24h_percent)


@router.callback_query(F.data == 'cn_period_current_price')
async def cn_ask_period_current_price_percent(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(CreateRequestFSM.get_ticker_name)
    data = await state.get_data()
    try:
        current_price = await repo.get_current_price(data['ticker_name'])
    except httpx.ConnectError:
        await callback.message.edit_text('Сервис временно недоступен', reply_markup=KB.main())
    else:
        if isinstance(current_price, str):
            await callback.message.edit_text(f'{current_price}', reply_markup=KB.main())
        else:
            msg = await callback.message.edit_text(t.ask_period_current_price_percent(current_price, 'USDT'),
                                                   reply_markup=KB.back_to_main())
            await state.update_data({'type_notice': 'period_current_price', 'msg': msg, 'current_price': current_price})
            await state.set_state(CreateRequestFSM.get_period_current_price_percent)


@router.callback_query(F.data == 'cn_period_point')
async def cn_ask_period_point(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(CreateRequestFSM.get_ticker_name)
    msg = await callback.message.edit_text(
        '<b><u>Уведомление сработает при изменении цены в % от указанной цены до указанного значения %.</u></b>\n\n'
        'Введите цену, от которой будет рассчитываться изменение:',
        reply_markup=KB.back_to_main())
    await state.update_data({'type_notice': 'period_point', 'msg': msg})
    await state.set_state(CreateRequestFSM.get_price)


@router.message(CreateRequestFSM.get_price)
async def cn_get_price(message: types.Message, state: FSMContext):
    await message.delete()
    data = await state.get_data()
    msg = await get_msg_from_state(state)
    price = await check_price(message.text)
    if not price:
        await msg.edit_text('Некорректное значение.\n'
                            'Попробуйте еще раз.',
                            reply_markup=KB.back_to_main())
    if data['type_notice'] == 'price_up':
        user_request = UserRequestSchema.create(data['ticker_name'], Price(target_price=price), Way.up_to)
        await Requests.add_request(message.from_user.id, user_request)
        await msg.edit_text(
            f'Создано уведомление!\n\n'
            f'Уведомлять при\n'
            f'повышении цены\n'
            f'{data["ticker_name"]}\n'
            f'до {price}',
            reply_markup=KB.back_to_main())
    if data['type_notice'] == 'price_down':
        user_request = UserRequestSchema.create(data['ticker_name'], Price(target_price=price), Way.down_to)
        await Requests.add_request(message.from_user.id, user_request)
        await msg.edit_text(
            f'Создано уведомление\n\n'
            f'Уведомлять при\n'
            f'снижении цены\n'
            f'{data["ticker_name"]}\n'
            f'до {price}',
            reply_markup=KB.back_to_main())
    if data['type_notice'] == 'period_point':
        msg = await msg.edit_text(
            '<b>Уведомление сработает при изменении цены в % '
            f'от указанной Вами цены <u>{price}</u> USDT.</b>\n\n'
            'Введите процент:',
            reply_markup=KB.back_to_main()
        )
        await state.update_data({'msg': msg, 'user_price': price})
        await state.set_state(CreateRequestFSM.get_period_point_percent)


@router.message(CreateRequestFSM.get_period_point_percent)
async def cn_get_period_point_percent(message: types.Message, state: FSMContext):
    await message.delete()
    data = await state.get_data()
    msg = await get_msg_from_state(state)
    percent = await check_percent(message.text)
    user_request = UserRequestSchema.create(data['ticker_name'],
                                            PercentOfPoint(target_percent=percent, current_price=data['user_price']),
                                            Way.all)
    try:
        await Requests.add_request(message.from_user.id, user_request)
        await msg.edit_text(
            f'Создано уведомление!\n\n'
            f'Уведомлять при\n'
            f'изменении цены {data["ticker_name"]} \n'
            f'на {percent}% от {data["user_price"]} USDT',
            reply_markup=KB.back_to_main())
    except Exception as e:
        await msg.edit_text(f'Ошибка создания уведомления: {str(e)}', reply_markup=KB.back_to_main())


@router.message(CreateRequestFSM.get_period_24h_percent)
async def cn_get_period_24h_percent(message: types.Message, state: FSMContext):
    await message.delete()
    data = await state.get_data()
    msg = await get_msg_from_state(state)
    percent = await check_percent(message.text)
    user_request = UserRequestSchema.create(data['ticker_name'],
                                            PercentOfTime(target_percent=percent, period=Period.v_24h),
                                            Way.all)
    try:
        await Requests.add_request(message.from_user.id, user_request)
        await msg.edit_text(
            f'Создано уведомление!\n\n'
            f'Уведомлять при\n'
            f'изменении цены {data["ticker_name"]} \n'
            f'на {percent}% за последние 24 часа',
            reply_markup=KB.back_to_main())
    except Exception as e:
        await msg.edit_text(f'Ошибка создания уведомления: {str(e)}', reply_markup=KB.back_to_main())
