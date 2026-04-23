from app.default_user import CURRENT_USER
from app.exceptions import ValidationException
from app.schema import initialize_database
from app.services.gambler_profile_service import GAME_TYPES, GamblerProfileService
from app.services.stake_management_service import StakeManagementService


APP_TITLE = "Gambling App - Gambler Profile Management"
MINIMUM_STAKE = 100.0


def print_header(title):
    print(f"\n{title}")
    print("-" * len(title))


def choose_option(prompt, valid_choices):
    while True:
        value = input(f"{prompt}: ").strip()
        if value in valid_choices:
            return value
        print(f"Choose one of these options: {', '.join(valid_choices)}")


def read_text(label):
    while True:
        value = input(f"{label}: ").strip()
        if value:
            return value
        print(f"{label} is required.")


def read_optional_text(label):
    return input(f"{label}: ").strip() or None


def read_number(label, minimum=None, maximum=None, greater_than=None, less_than=None):
    rules = []
    if minimum is not None:
        rules.append(f">= {minimum}")
    if maximum is not None:
        rules.append(f"<= {maximum}")
    if greater_than is not None:
        rules.append(f"> {greater_than}")
    if less_than is not None:
        rules.append(f"< {less_than}")

    prompt = label if not rules else f"{label} ({', '.join(str(rule) for rule in rules)})"

    while True:
        raw_value = input(f"{prompt}: ").strip()
        try:
            value = float(raw_value)
        except ValueError:
            print("Enter a valid number.")
            continue

        if minimum is not None and value < minimum:
            print(f"Value must be at least {minimum}.")
            continue
        if maximum is not None and value > maximum:
            print(f"Value must be at most {maximum}.")
            continue
        if greater_than is not None and value <= greater_than:
            print(f"Value must be greater than {greater_than}.")
            continue
        if less_than is not None and value >= less_than:
            print(f"Value must be less than {less_than}.")
            continue
        return value


def read_int(label, minimum=None):
    while True:
        raw_value = input(f"{label}{f' (>= {minimum})' if minimum is not None else ''}: ").strip()
        try:
            value = int(raw_value)
        except ValueError:
            print("Enter a whole number.")
            continue

        if minimum is not None and value < minimum:
            print(f"Value must be at least {minimum}.")
            continue
        return value


def choose_game_type():
    print_header("Game Types")
    for index, game_type in enumerate(GAME_TYPES, start=1):
        print(f"{index}. {game_type}")

    choice = choose_option("Choose game type", [str(index) for index in range(1, len(GAME_TYPES) + 1)])
    return GAME_TYPES[int(choice) - 1]


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
        print(
            f"{gambler['id']}. {gambler['full_name']} | "
            f"{gambler['email']} | "
            f"{gambler['phone_number']} | "
            f"Stake: {gambler['current_stake']:.2f} | "
            f"Status: {gambler['account_status']}"
        )


def show_gambler_details(stats):
    print_header("User Details")
    print(f"Name: {stats.full_name}")
    print(f"Email: {stats.email}")
    print(f"Phone Number: {stats.phone_number}")
    print(f"Current Stake: {stats.current_stake:.2f}")
    print(f"Initial Stake: {stats.initial_stake:.2f}")
    print(f"Win Threshold: {stats.win_threshold:.2f}")
    print(f"Loss Threshold: {stats.loss_threshold:.2f}")
    print(f"Threshold Status: {stats.threshold_status}")
    print(f"Total Bets: {stats.total_bets}")
    print(f"Total Wins: {stats.total_wins}")
    print(f"Total Losses: {stats.total_losses}")
    print(f"Total Winnings: {stats.total_winnings:.2f}")
    print(f"Net Profit/Loss: {stats.net_profit_loss:.2f}")
    print(f"Win Rate: {stats.win_rate:.2f}%")
    print(f"Account Status: {stats.account_status}")
    print(f"Game Type: {stats.preferred_game_type}")
    print(f"Min Bet: {stats.min_bet:.2f}")
    print(f"Max Bet: {stats.max_bet:.2f}")
    print(f"Session Game Limit: {stats.session_game_limit}")
    print(f"Notes: {stats.notes}")


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
        print(
            f"{transaction.transaction_id}. {transaction.transaction_type} | "
            f"Amount: {transaction.amount:.2f} | "
            f"Before: {transaction.balance_before:.2f} | "
            f"After: {transaction.balance_after:.2f} | "
            f"{transaction.created_at}"
        )
        if transaction.note:
            print(f"   {transaction.note}")


def collect_user_data():
    full_name = read_text("Name")
    email = read_text("Email")
    phone_number = read_text("Phone Number")
    initial_stake = read_number("Initial Stake", minimum=MINIMUM_STAKE)
    win_threshold = read_number("Win Threshold", greater_than=initial_stake)
    loss_threshold = read_number("Loss Threshold", minimum=0, less_than=initial_stake)
    min_bet = read_number("Minimum Bet", minimum=0.01, maximum=initial_stake)
    max_bet = read_number("Maximum Bet", minimum=min_bet, maximum=initial_stake)
    preferred_game_type = choose_game_type()
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
    print("1. Win")
    print("2. Loss")
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
    while True:
        print_header("Stake Management Menu")
        print("1. Initialize stake")
        print("2. Deposit stake")
        print("3. Withdraw stake")
        print("4. Record bet result")
        print("5. Adjust current stake")
        print("6. Validate boundaries")
        print("7. Stake monitor summary")
        print("8. Stake history report")
        print("9. Back")

        choice = choose_option("Choose an option", ["1", "2", "3", "4", "5", "6", "7", "8", "9"])

        if choice == "1":
            initialize_stake_flow(service, gambler_id)
        elif choice == "2":
            deposit_stake_flow(service, gambler_id)
        elif choice == "3":
            withdraw_stake_flow(service, gambler_id)
        elif choice == "4":
            bet_result_flow(service, gambler_id)
        elif choice == "5":
            adjust_stake_flow(service, gambler_id)
        elif choice == "6":
            show_boundary_status(service.validate_boundaries(gambler_id))
        elif choice == "7":
            show_monitor_summary(service.get_monitor_summary(gambler_id))
        elif choice == "8":
            show_history_report(service.get_history_report(gambler_id))
        else:
            return


def selected_user_menu(profile_service, stake_service, gambler_id):
    while True:
        print_header("Selected User Menu")
        print("1. View user details")
        print("2. Update user")
        print("3. Validate user")
        print("4. Reset user")
        print("5. Deactivate user")
        print("6. Stake management")
        print("7. Back")

        choice = choose_option("Choose an option", ["1", "2", "3", "4", "5", "6", "7"])

        if choice == "1":
            show_gambler_details(profile_service.retrieve_gambler_statistics(gambler_id))
        elif choice == "2":
            update_user_flow(profile_service, gambler_id)
        elif choice == "3":
            validate_user_flow(profile_service, gambler_id)
        elif choice == "4":
            reset_user_flow(profile_service, gambler_id)
        elif choice == "5":
            profile_service.deactivate_gambler(gambler_id)
            print("User deactivated.")
        elif choice == "6":
            stake_management_menu(stake_service, gambler_id)
        else:
            return


def main():
    init_result = initialize_database()
    profile_service = GamblerProfileService(minimum_stake=MINIMUM_STAKE)
    stake_service = StakeManagementService()
    profile_service.ensure_gambler_exists(CURRENT_USER)
    show_startup_info(init_result)

    while True:
        try:
            print_header("Main Menu")
            print("1. Create new user")
            print("2. Current user")
            print("3. Show users")
            print("4. Exit")

            choice = choose_option("Choose an option", ["1", "2", "3", "4"])

            if choice == "1":
                create_user_flow(profile_service)
            elif choice == "2":
                gambler_id = choose_current_user(profile_service)
                if gambler_id is not None:
                    selected_user_menu(profile_service, stake_service, gambler_id)
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
