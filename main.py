from app.default_user import CURRENT_USER
from app.exceptions import ValidationException
from app.schema import initialize_database
from app.services.betting_service import ODDS_TYPES, OUTCOME_STRATEGIES, STRATEGY_TYPES, BettingService
from app.services.game_session_service import GameSessionService
from app.services.gambler_profile_service import GAME_TYPES, GAME_TYPE_PROBABILITIES, GamblerProfileService
from app.services.stake_management_service import StakeManagementService
from app.services.win_loss_service import WinLossService
from app.validation import InputValidator, SafeInputHandler, ValidationConfig


APP_TITLE = "Gambling App - Gambler Profile Management"
MINIMUM_STAKE = 100.0
validator = InputValidator(ValidationConfig(min_stake=MINIMUM_STAKE, allow_zero_stake=True))
input_handler = SafeInputHandler(validator)


def print_header(title):
    print(f"\n{title}")
    print("-" * len(title))


def choose_option(prompt, valid_choices):
    while True:
        value = input(f"{prompt}: ").strip()
        if value in valid_choices:
            return value
        print(f"Choose one of these options: {', '.join(valid_choices)}")


def build_rules(minimum=None, maximum=None, greater_than=None, less_than=None):
    rules = []
    if minimum is not None:
        rules.append(f">= {minimum}")
    if maximum is not None:
        rules.append(f"<= {maximum}")
    if greater_than is not None:
        rules.append(f"> {greater_than}")
    if less_than is not None:
        rules.append(f"< {less_than}")
    return rules


def check_numeric_constraints(value, minimum=None, maximum=None, greater_than=None, less_than=None):
    if minimum is not None and value < minimum:
        return f"Value must be at least {minimum}."
    if maximum is not None and value > maximum:
        return f"Value must be at most {maximum}."
    if greater_than is not None and value <= greater_than:
        return f"Value must be greater than {greater_than}."
    if less_than is not None and value >= less_than:
        return f"Value must be less than {less_than}."
    return None


def read_number(label, minimum=None, maximum=None, greater_than=None, less_than=None):
    rules = build_rules(minimum, maximum, greater_than, less_than)
    prompt = label if not rules else f"{label} ({', '.join(str(r) for r in rules)})"
    while True:
        try:
            value = input_handler.prompt_number(prompt)
        except ValidationException as error:
            print(error)
            continue
        error_msg = check_numeric_constraints(value, minimum, maximum, greater_than, less_than)
        if error_msg:
            print(error_msg)
            continue
        return value


def read_int(label, minimum=None, maximum=None):
    rules = build_rules(minimum, maximum)
    prompt = f"{label}{' (' + ', '.join(rules) + ')' if rules else ''}"
    while True:
        value = input_handler.prompt_int(prompt, minimum=minimum)
        if maximum is not None and value > maximum:
            print(f"{label} must be at most {maximum}.")
            continue
        return value


def show_menu(title, options, skip_prompt=False):
    print_header(title)
    for i, opt in enumerate(options, 1):
        print(f"{i}. {opt}")
    if skip_prompt:
        return None
    valid = [str(i) for i in range(1, len(options) + 1)]
    return choose_option("Choose an option", valid)


def select_game_type():
    choice = show_menu("Game Types", GAME_TYPES)
    return GAME_TYPES[int(choice) - 1]


def select_strategy_type():
    choice = show_menu("Betting Strategies", STRATEGY_TYPES)
    return STRATEGY_TYPES[int(choice) - 1]


def select_outcome_strategy():
    choice = show_menu("Outcome Strategies", OUTCOME_STRATEGIES)
    return OUTCOME_STRATEGIES[int(choice) - 1]


def select_odds_type():
    choice = show_menu("Odds Types", ODDS_TYPES)
    return ODDS_TYPES[int(choice) - 1]


def choose_game_type():
    return select_game_type()


def choose_strategy_type():
    return select_strategy_type()


def choose_outcome_strategy():
    return select_outcome_strategy()


def choose_odds_type():
    return select_odds_type()


def show_startup_info(init_result):
    print_header(APP_TITLE)
    print(f"Database: {init_result['database']}")
    print(f"Tables: {', '.join(init_result['tables'])}")


def show_gambler_list(gamblers):
    print_header("Current Users")
    if not gamblers:
        print("No users found.")
        return
    for gambler in gamblers:
        print(f"{gambler['id']}. {gambler['full_name']} | {gambler['email']} | {gambler['phone_number']} | Stake: {gambler['current_stake']:.2f} | Status: {gambler['account_status']}")


def show_gambler_details(stats):
    print_header("User Details")
    details = [
        f"Name: {stats.full_name}",
        f"Email: {stats.email}",
        f"Phone Number: {stats.phone_number}",
        f"Current Stake: {stats.current_stake:.2f}",
        f"Initial Stake: {stats.initial_stake:.2f}",
        f"Win Threshold: {stats.win_threshold:.2f}",
        f"Loss Threshold: {stats.loss_threshold:.2f}",
        f"Threshold Status: {stats.threshold_status}",
        f"Total Bets: {stats.total_bets}",
        f"Total Wins: {stats.total_wins}",
        f"Total Losses: {stats.total_losses}",
        f"Total Winnings: {stats.total_winnings:.2f}",
        f"Net Profit/Loss: {stats.net_profit_loss:.2f}",
        f"Win Rate: {stats.win_rate:.2f}%",
        f"Account Status: {stats.account_status}",
        f"Game Type: {stats.preferred_game_type}",
        f"Min Bet: {stats.min_bet:.2f}",
        f"Max Bet: {stats.max_bet:.2f}",
        f"Session Game Limit: {stats.session_game_limit}",
        f"Notes: {stats.notes}",
    ]
    for detail in details:
        print(detail)


def show_boundary_status(status):
    print_header("Stake Boundary Status")
    print(f"Current Stake: {status.current_stake:.2f}")
    print(f"Upper Limit: {status.upper_limit:.2f}")
    print(f"Lower Limit: {status.lower_limit:.2f}")
    print(f"Warning Level: {status.warning_level}")
    print(f"Within Bounds: {'Yes' if status.within_bounds else 'No'}")


def show_monitor_summary(summary):
    print_header("Stake Monitor Summary")
    print(f"Current Stake: {summary.current_stake:.2f}")
    print(f"Peak Stake: {summary.peak_stake:.2f}")
    print(f"Lowest Stake: {summary.lowest_stake:.2f}")
    print(f"Total Change: {summary.total_change:.2f}")
    print(f"Volatility: {summary.volatility:.2f}")
    print(f"Transaction Count: {summary.transaction_count}")


def show_history_report(report):
    print_header("Stake History Report")
    print(f"Gambler ID: {report.gambler_id}")
    print(f"Current Stake: {report.current_stake:.2f}")
    print(f"Total Transactions: {report.total_transactions}")
    print(f"Deposits Total: {report.deposits_total:.2f}")
    print(f"Withdrawals Total: {report.withdrawals_total:.2f}")
    print(f"Bet Wins Total: {report.bet_wins_total:.2f}")
    print(f"Bet Losses Total: {report.bet_losses_total:.2f}")
    print(f"Adjustments Total: {report.adjustments_total:.2f}")
    print(f"Net Change: {report.net_change:.2f}")
    print_header("Transactions")
    if not report.transactions:
        print("No stake transactions found.")
        return
    for transaction in report.transactions:
        print(f"{transaction.transaction_id}. {transaction.transaction_type} | Amount: {transaction.amount:.2f} | Before: {transaction.balance_before:.2f} | After: {transaction.balance_after:.2f} | {transaction.created_at}")
        if transaction.note:
            print(f"   {transaction.note}")


def show_bet_record(bet):
    print_header("Bet Result")
    print(f"Bet ID: {bet.bet_id}")
    print(f"Strategy: {bet.strategy_type}")
    print(f"Amount: {bet.bet_amount:.2f}")
    print(f"Win Probability: {bet.win_probability:.2f}")
    print(f"Odds Multiplier: {bet.odds_multiplier:.2f}")
    print(f"Outcome: {bet.outcome}")
    print(f"Payout: {bet.payout_amount:.2f}")
    print(f"Stake Before: {bet.stake_before:.2f}")
    print(f"Stake After: {bet.stake_after:.2f}")
    print(f"Placed At: {bet.placed_at}")


def show_betting_session_summary(summary):
    print_header("Betting Session Summary")
    print(f"Session ID: {summary.session_id}")
    print(f"Strategy: {summary.strategy_type}")
    print(f"Total Bets: {summary.total_bets}")
    print(f"Total Wins: {summary.total_wins}")
    print(f"Total Losses: {summary.total_losses}")
    print(f"Total Profit: {summary.total_profit:.2f}")
    print(f"Started At: {summary.started_at}")
    print(f"Ended At: {summary.ended_at}")
    print_header("Session Bets")
    if not summary.bets:
        print("No bets found.")
        return
    for bet in summary.bets:
        print(f"{bet.bet_id}. {bet.strategy_type} | Amount: {bet.bet_amount:.2f} | Outcome: {bet.outcome} | Payout: {bet.payout_amount:.2f} | Stake After: {bet.stake_after:.2f}")


def show_recent_bets(bets):
    print_header("Recent Bets")
    if not bets:
        print("No bets found.")
        return
    for bet in bets:
        print(f"{bet.bet_id}. {bet.strategy_type} | Amount: {bet.bet_amount:.2f} | Outcome: {bet.outcome} | Payout: {bet.payout_amount:.2f} | Stake After: {bet.stake_after:.2f} | {bet.placed_at}")


def get_betting_limits(profile_service, gambler_id):
    stats = profile_service.retrieve_gambler_statistics(gambler_id)
    return {
        "min_bet": float(stats.min_bet),
        "max_bet": float(stats.max_bet),
        "current_stake": float(stats.current_stake),
    }


def show_session_list(sessions):
    print_header("Game Sessions")
    if not sessions:
        print("No game sessions found.")
        return
    for session in sessions:
        default_bet = session.get('default_bet_amount') or 0
        print(f"{session['id']}. Status: {session['status']} | Default Bet: {default_bet:.2f} | Games: {session['total_games_played']}/{session['max_games']} | Profit: {session['total_profit']:.2f} | Started: {session['started_at']}")


def show_game_session_summary(summary):
    print_header("Game Session Summary")
    details = [
        f"Session ID: {summary.session_id}",
        f"Status: {summary.status}",
        f"End Reason: {summary.end_reason}",
        f"Default Bet Amount: {summary.default_bet_amount:.2f}",
        f"Default Win Probability: {summary.default_win_probability:.2f}",
        f"Max Games: {summary.max_games}",
        f"Total Games Played: {summary.total_games_played}",
        f"Total Wins: {summary.total_wins}",
        f"Total Losses: {summary.total_losses}",
        f"Total Profit: {summary.total_profit:.2f}",
        f"Current Stake: {summary.current_stake:.2f}",
        f"Started At: {summary.started_at}",
        f"Ended At: {summary.ended_at}",
        f"Total Pause Seconds: {summary.total_pause_seconds}",
    ]
    for detail in details:
        print(detail)
    print_header("Games")
    if not summary.games:
        print("No games played yet.")
    else:
        for game in summary.games:
            print(f"{game.game_number}. Bet #{game.bet_id} | Amount: {game.bet_amount:.2f} | Outcome: {game.outcome} | Payout: {game.payout_amount:.2f} | Stake After: {game.stake_after:.2f}")
    print_header("Pauses")
    if not summary.pauses:
        print("No pauses recorded.")
    else:
        for pause in summary.pauses:
            print(f"{pause.pause_id}. {pause.pause_reason} | Paused: {pause.paused_at} | Resumed: {pause.resumed_at} | Seconds: {pause.pause_seconds}")


def show_win_loss_statistics(stats):
    print_header("Win/Loss Statistics")
    details = [
        f"Total Games: {stats.total_games}",
        f"Wins: {stats.wins}",
        f"Losses: {stats.losses}",
        f"Win Rate: {stats.win_rate:.2f}%",
        f"Loss Rate: {stats.loss_rate:.2f}%",
        f"Win/Loss Ratio: {stats.win_loss_ratio}",
        f"Total Winnings: {stats.total_winnings:.2f}",
        f"Total Losses: {stats.total_losses_amount:.2f}",
        f"Net Profit/Loss: {stats.net_profit_loss:.2f}",
        f"Average Win: {stats.average_win:.2f}",
        f"Average Loss: {stats.average_loss:.2f}",
        f"Largest Win: {stats.largest_win:.2f}",
        f"Largest Loss: {stats.largest_loss:.2f}",
        f"Current Win Streak: {stats.current_win_streak}",
        f"Current Loss Streak: {stats.current_loss_streak}",
        f"Longest Win Streak: {stats.longest_win_streak}",
        f"Longest Loss Streak: {stats.longest_loss_streak}",
        f"Profit Factor: {stats.profit_factor}",
    ]
    for detail in details:
        print(detail)


def show_running_totals(summary):
    print_header("Running Totals")
    print(f"Total Games: {summary.total_games}")
    print(f"Current Balance: {summary.current_balance:.2f}")
    print(f"Net Profit/Loss: {summary.net_profit_loss:.2f}")
    print(f"Balance History: {', '.join(f'{balance:.2f}' for balance in summary.balance_history) if summary.balance_history else 'No history'}")
    print_header("Recent Results")
    if not summary.last_results:
        print("No results found.")
        return
    for result in summary.last_results:
        print(f"{result.result_id}. {result.result_type} | Net Change: {result.net_change:.2f} | Stake After: {result.stake_after:.2f} | Win Streak: {result.current_win_streak} | Loss Streak: {result.current_loss_streak}")


def show_recent_game_results(results):
    print_header("Recent Game Results")
    if not results:
        print("No results found.")
        return
    for result in results:
        print(f"{result.result_id}. {result.result_type} | Strategy: {result.outcome_strategy} | Payout: {result.payout_amount:.2f} | Net Change: {result.net_change:.2f} | Stake After: {result.stake_after:.2f} | {result.created_at}")


def collect_user_data():
    full_name = input_handler.prompt_name("Name")
    email = input_handler.prompt_email("Email")
    phone_number = input_handler.prompt_phone_number("Phone Number")
    initial_stake = read_number("Initial Stake", minimum=MINIMUM_STAKE)
    win_threshold = read_number("Win Threshold", greater_than=initial_stake)
    loss_threshold = read_number("Loss Threshold", minimum=0, less_than=initial_stake)
    min_bet = read_number("Minimum Bet", minimum=0.01, maximum=initial_stake)
    max_bet = read_number("Maximum Bet", minimum=min_bet, maximum=initial_stake)
    preferred_game_type = select_game_type()
    session_game_limit = read_int("Session Game Limit", minimum=1)
    notes = read_optional_text("Notes")
    return {
        "full_name": full_name,
        "email": email,
        "phone_number": phone_number,
        "initial_stake": initial_stake,
        "win_threshold": win_threshold,
        "loss_threshold": loss_threshold,
        "preferences": {
            "min_bet": min_bet,
            "max_bet": max_bet,
            "preferred_game_type": preferred_game_type,
            "session_game_limit": session_game_limit,
            "notes": notes,
        },
    }


def create_user_flow(service):
    print_header("Create New User")
    user_data = collect_user_data()
    service.create_gambler(
        full_name=user_data["full_name"],
        email=user_data["email"],
        phone_number=user_data["phone_number"],
        initial_stake=user_data["initial_stake"],
        win_threshold=user_data["win_threshold"],
        loss_threshold=user_data["loss_threshold"],
        preferences=user_data["preferences"],
    )
    print("User created successfully.")


def choose_current_user(service):
    gamblers = service.list_gamblers()
    show_gambler_list(gamblers)
    if not gamblers:
        return None
    valid_ids = [str(gambler["id"]) for gambler in gamblers]
    selected_id = choose_option("Enter user id", valid_ids)
    return int(selected_id)


def update_user_flow(service, gambler_id):
    print_header("Update User")
    user_data = collect_user_data()
    current_stake = read_number("Current Stake", minimum=0)
    service.update_gambler(
        gambler_id,
        profile_updates={
            "full_name": user_data["full_name"],
            "email": user_data["email"],
            "phone_number": user_data["phone_number"],
            "initial_stake": user_data["initial_stake"],
            "current_stake": current_stake,
            "win_threshold": user_data["win_threshold"],
            "loss_threshold": user_data["loss_threshold"],
        },
        preference_updates=user_data["preferences"],
    )
    print("User updated successfully.")


def validate_user_flow(service, gambler_id):
    result = service.validate_gambler_eligibility(gambler_id)
    print_header("Eligibility Result")
    print(f"Eligible: {'Yes' if result['is_eligible'] else 'No'}")
    for reason in result["reasons"]:
        print(f"- {reason}")


def reset_user_flow(service, gambler_id):
    new_initial_stake = read_number("New Initial Stake", minimum=MINIMUM_STAKE)
    result = service.reset_gambler_profile(gambler_id, new_initial_stake)
    print_header("Profile Reset")
    print(f"New Initial Stake: {result['new_initial_stake']:.2f}")
    print(f"New Win Threshold: {result['new_win_threshold']:.2f}")
    print(f"New Loss Threshold: {result['new_loss_threshold']:.2f}")


def initialize_stake_flow(service, gambler_id):
    amount = read_number("Initialize Stake Amount", minimum=0.01)
    note = read_optional_text("Note")
    service.initialize_stake(gambler_id, amount, note or "Stake initialized from menu")
    print("Stake initialized successfully.")


def deposit_stake_flow(service, gambler_id):
    amount = read_number("Deposit Amount", minimum=0.01)
    note = read_optional_text("Note")
    service.deposit_stake(gambler_id, amount, note or "Deposit from menu")
    print("Deposit recorded successfully.")


def withdraw_stake_flow(service, gambler_id):
    amount = read_number("Withdrawal Amount", minimum=0.01)
    note = read_optional_text("Note")
    service.withdraw_stake(gambler_id, amount, note or "Withdrawal from menu")
    print("Withdrawal recorded successfully.")


def bet_result_flow(service, gambler_id):
    amount = read_number("Bet Result Amount", minimum=0.01)
    print("1. Win\n2. Loss")
    outcome_choice = choose_option("Choose outcome", ["1", "2"])
    outcome = "WIN" if outcome_choice == "1" else "LOSS"
    note = read_optional_text("Note")
    service.apply_bet_result(gambler_id, amount, outcome, note or f"Bet {outcome.lower()} recorded from menu")
    print("Bet result recorded successfully.")


def adjust_stake_flow(service, gambler_id):
    amount = read_number("New Current Stake", minimum=0)
    note = read_optional_text("Note")
    service.adjust_stake(gambler_id, amount, note or "Manual stake adjustment")
    print("Stake adjusted successfully.")


def stake_management_menu(service, gambler_id):
    options = ["Initialize stake", "Deposit stake", "Withdraw stake", "Record bet result", "Adjust current stake", "Validate boundaries", "Stake monitor summary", "Stake history report", "Back"]
    flows = [
        lambda: initialize_stake_flow(service, gambler_id),
        lambda: deposit_stake_flow(service, gambler_id),
        lambda: withdraw_stake_flow(service, gambler_id),
        lambda: bet_result_flow(service, gambler_id),
        lambda: adjust_stake_flow(service, gambler_id),
        lambda: show_boundary_status(service.validate_boundaries(gambler_id)),
        lambda: show_monitor_summary(service.get_monitor_summary(gambler_id)),
        lambda: show_history_report(service.get_history_report(gambler_id)),
    ]
    while True:
        choice = show_menu("Stake Management Menu", options)
        if choice == "9":
            return
        flows[int(choice) - 1]()


def place_single_bet_flow(profile_service, service, gambler_id):
    limits = get_betting_limits(profile_service, gambler_id)
    amount = read_number("Bet Amount", minimum=limits["min_bet"], maximum=min(limits["max_bet"], limits["current_stake"]))
    game_type = select_game_type()
    probability = read_probability() if game_type == "CUSTOM" else GAME_TYPE_PROBABILITIES[game_type]
    outcome_strategy = select_outcome_strategy()
    house_edge = read_number("House Edge", minimum=0, less_than=1) if outcome_strategy == "WEIGHTED" else 0
    odds_type = select_odds_type()
    fixed_odds = read_number("Fixed Odds Multiplier", greater_than=1) if odds_type == "FIXED" else None
    bet = service.place_bet(
        gambler_id,
        amount,
        probability,
        "FIXED_AMOUNT",
        outcome_strategy=outcome_strategy,
        house_edge=house_edge,
        odds_type=odds_type,
        fixed_odds=fixed_odds,
    )
    show_bet_record(bet)


def place_strategy_bets_flow(profile_service, service, gambler_id):
    limits = get_betting_limits(profile_service, gambler_id)
    strategy_type = select_strategy_type()
    game_type = select_game_type()
    probability = read_probability() if game_type == "CUSTOM" else GAME_TYPE_PROBABILITIES[game_type]
    outcome_strategy = select_outcome_strategy()
    house_edge = read_number("House Edge", minimum=0, less_than=1) if outcome_strategy == "WEIGHTED" else 0
    odds_type = select_odds_type()
    fixed_odds = read_number("Fixed Odds Multiplier", greater_than=1) if odds_type == "FIXED" else None
    rounds = read_int("Number of Bets", minimum=1)
    fixed_amount = None
    percentage_value = None
    if strategy_type in {"FIXED_AMOUNT", "MARTINGALE", "REVERSE_MARTINGALE", "FIBONACCI", "DALEMBERT"}:
        fixed_amount = read_number("Base Bet Amount", minimum=limits["min_bet"], maximum=min(limits["max_bet"], limits["current_stake"]))
    elif strategy_type == "PERCENTAGE":
        percentage_value = read_number("Percentage of Current Stake", greater_than=0, less_than=100)
    summary = service.place_bet_with_strategy(
        gambler_id,
        strategy_type,
        probability,
        fixed_amount=fixed_amount,
        percentage_value=percentage_value,
        rounds=rounds,
        outcome_strategy=outcome_strategy,
        house_edge=house_edge,
        odds_type=odds_type,
        fixed_odds=fixed_odds,
    )
    show_betting_session_summary(summary)


def betting_menu(profile_service, service, gambler_id):
    options = ["Place single bet", "Place strategy bets", "Show recent bets", "Back"]
    flows = [
        lambda: place_single_bet_flow(profile_service, service, gambler_id),
        lambda: place_strategy_bets_flow(profile_service, service, gambler_id),
        lambda: show_recent_bets(service.get_recent_bets(gambler_id)),
    ]
    while True:
        choice = show_menu("Betting Menu", options)
        if choice == "4":
            return
        flows[int(choice) - 1]()


def preview_outcome_flow(service):
    probability = read_probability()
    outcome_strategy = select_outcome_strategy()
    house_edge = read_number("House Edge", minimum=0, less_than=1) if outcome_strategy == "WEIGHTED" else 0
    result = service.determine_bet_outcome(probability, outcome_strategy, house_edge)
    print_header("Outcome Preview")
    print(f"Outcome: {result}")


def win_loss_menu(win_loss_service, betting_service, gambler_id):
    options = ["Win/loss statistics", "Running totals", "Recent game results", "Preview outcome", "Back"]
    flows = [
        lambda: show_win_loss_statistics(win_loss_service.get_win_loss_statistics(gambler_id)),
        lambda: show_running_totals(win_loss_service.get_running_totals(gambler_id)),
        lambda: show_recent_game_results(win_loss_service.get_recent_results(gambler_id)),
        lambda: preview_outcome_flow(betting_service),
    ]
    while True:
        choice = show_menu("Win/Loss Menu", options)
        if choice == "5":
            return
        flows[int(choice) - 1]()


def start_game_session_flow(profile_service, service, gambler_id):
    stats = profile_service.retrieve_gambler_statistics(gambler_id)
    game_type = stats.preferred_game_type
    default_bet_amount = read_number("Default Bet Amount", minimum=0.01)
    default_win_probability = read_probability() if game_type == "CUSTOM" else GAME_TYPE_PROBABILITIES[game_type]
    max_games = read_int("Max Games", minimum=1, maximum=stats.session_game_limit)
    session_id = service.start_new_session(gambler_id, default_bet_amount, default_win_probability, max_games)
    print(f"Game session created successfully. Session ID: {session_id}")
    show_game_session_summary(service.get_session_summary(session_id))


def choose_game_session(service, gambler_id):
    sessions = service.list_sessions(gambler_id)
    show_session_list(sessions)
    if not sessions:
        return None
    valid_ids = [str(session["id"]) for session in sessions]
    session_id = choose_option("Enter session id", valid_ids)
    return int(session_id)


def play_one_game_flow(profile_service, service, session_id):
    custom_choice = choose_option("Use session defaults? 1 for yes, 2 for no", ["1", "2"])
    if custom_choice == "1":
        results = service.play_games(session_id, 1)
    else:
        bet_amount = read_number("Bet Amount", minimum=0.01)
        game_type = select_game_type()
        probability = read_probability() if game_type == "CUSTOM" else GAME_TYPE_PROBABILITIES[game_type]
        results = service.play_games(session_id, 1, bet_amount, probability)
    if results:
        show_bet_record(results[-1])


def autoplay_session_flow(profile_service, service, session_id):
    games_count = read_int("How many games to autoplay", minimum=1)
    custom_choice = choose_option("Use session defaults? 1 for yes, 2 for no", ["1", "2"])
    if custom_choice == "1":
        service.play_games(session_id, games_count)
    else:
        bet_amount = read_number("Bet Amount", minimum=0.01)
        game_type = select_game_type()
        probability = read_probability() if game_type == "CUSTOM" else GAME_TYPE_PROBABILITIES[game_type]
        service.play_games(session_id, games_count, bet_amount, probability)
    show_game_session_summary(service.get_session_summary(session_id))


def pause_session_flow(service, session_id):
    reason = read_text("Pause Reason")
    service.pause_session(session_id, reason)
    print("Session paused.")


def resume_session_flow(service, session_id):
    service.resume_session(session_id)
    print("Session resumed.")


def end_session_flow(service, session_id):
    service.end_session(session_id)
    print("Session ended.")


def game_session_detail_menu(profile_service, service, session_id):
    options = ["View session summary", "Play one game", "Autoplay multiple games", "Pause session", "Resume session", "End session", "Back"]
    flows = [
        lambda: show_game_session_summary(service.get_session_summary(session_id)),
        lambda: play_one_game_flow(profile_service, service, session_id),
        lambda: autoplay_session_flow(profile_service, service, session_id),
        lambda: pause_session_flow(service, session_id),
        lambda: resume_session_flow(service, session_id),
        lambda: end_session_flow(service, session_id),
    ]
    while True:
        choice = show_menu("Game Session Menu", options)
        if choice == "7":
            return
        flows[int(choice) - 1]()


def game_sessions_menu(profile_service, service, gambler_id):
    options = ["Start new session", "Open session", "Show all sessions", "Back"]
    while True:
        choice = show_menu("Game Sessions Menu", options)
        if choice == "1":
            start_game_session_flow(profile_service, service, gambler_id)
        elif choice == "2":
            session_id = choose_game_session(service, gambler_id)
            if session_id is not None:
                game_session_detail_menu(profile_service, service, session_id)
        elif choice == "3":
            show_session_list(service.list_sessions(gambler_id))
        else:
            return


def selected_user_menu(profile_service, stake_service, betting_service, win_loss_service, game_session_service, gambler_id):
    options = ["View user details", "Update user", "Validate user", "Reset user", "Deactivate user", "Stake management", "Betting", "Win/loss analytics", "Game sessions", "Back"]
    flows = [
        lambda: show_gambler_details(profile_service.retrieve_gambler_statistics(gambler_id)),
        lambda: update_user_flow(profile_service, gambler_id),
        lambda: validate_user_flow(profile_service, gambler_id),
        lambda: reset_user_flow(profile_service, gambler_id),
        lambda: (profile_service.deactivate_gambler(gambler_id), print("User deactivated.")),
        lambda: stake_management_menu(stake_service, gambler_id),
        lambda: betting_menu(profile_service, betting_service, gambler_id),
        lambda: win_loss_menu(win_loss_service, betting_service, gambler_id),
        lambda: game_sessions_menu(profile_service, game_session_service, gambler_id),
    ]
    while True:
        choice = show_menu("Selected User Menu", options)
        if choice == "10":
            return
        flows[int(choice) - 1]()


def main():
    init_result = initialize_database()
    profile_service = GamblerProfileService(minimum_stake=MINIMUM_STAKE)
    stake_service = StakeManagementService()
    betting_service = BettingService()
    win_loss_service = WinLossService()
    game_session_service = GameSessionService(betting_service)
    profile_service.ensure_gambler_exists(CURRENT_USER)
    show_startup_info(init_result)
    show_menu("Main Menu", ["Create new user", "Current user", "Show users", "Exit"], skip_prompt=True)
    while True:
        try:
            choice = choose_option("Choose an option", ["1", "2", "3", "4"])
            if choice == "1":
                create_user_flow(profile_service)
            elif choice == "2":
                gambler_id = choose_current_user(profile_service)
                if gambler_id is not None:
                    selected_user_menu(profile_service, stake_service, betting_service, win_loss_service, game_session_service, gambler_id)
            elif choice == "3":
                show_gambler_list(profile_service.list_gamblers())
            else:
                print("Exiting application.")
                return
        except ValidationException as error:
            print(f"Validation error: {error}")
        except KeyboardInterrupt:
            print("\nReturning to menu.")


if __name__ == "__main__":
    main()
