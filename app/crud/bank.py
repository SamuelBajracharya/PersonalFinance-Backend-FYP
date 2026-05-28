from sqlalchemy.orm import Session
from sqlalchemy import func
import uuid
from datetime import datetime, timedelta

from app.models.bank import BankAccount, Transaction
from app.schemas.bank import TransactionCreate
from app.utils.auth import encrypt_user_data, decrypt_user_data


def _decrypt_bank_account(account, user_id: str):
    if account:
        account.account_number_masked = decrypt_user_data(account.account_number_masked, user_id)
        account.bank_token = decrypt_user_data(account.bank_token, user_id)
    return account


def _decrypt_transaction(tx, user_id: str):
    if tx:
        tx.description = decrypt_user_data(tx.description, user_id)
        tx.merchant = decrypt_user_data(tx.merchant, user_id)
    return tx


def get_bank_account(db: Session, bank_account_id: uuid.UUID):
    account = db.query(BankAccount).filter(BankAccount.id == bank_account_id).first()
    if account:
        _decrypt_bank_account(account, account.user_id)
    return account


def get_bank_accounts_by_user(db: Session, user_id: str):
    accounts = db.query(BankAccount).filter(BankAccount.user_id == user_id).all()
    for account in accounts:
        _decrypt_bank_account(account, user_id)
    return accounts


def get_bank_account_by_user_and_bank_name(db: Session, user_id: str, bank_name: str):
    account = (
        db.query(BankAccount)
        .filter(BankAccount.user_id == user_id, BankAccount.bank_name == bank_name)
        .first()
    )
    if account:
        _decrypt_bank_account(account, user_id)
    return account


def deactivate_bank_accounts_by_user(db: Session, user_id: str):
    db.query(BankAccount).filter(BankAccount.user_id == user_id).update(
        {BankAccount.is_active: False}, synchronize_session=False
    )
    db.commit()


def delete_transactions_by_user(db: Session, user_id: str):
    db.query(Transaction).filter(Transaction.user_id == user_id).delete()
    db.commit()


def create_transaction(db: Session, transaction: TransactionCreate, user_id: str):
    tx_data = transaction.model_dump()
    if tx_data.get("description"):
        tx_data["description"] = encrypt_user_data(tx_data["description"], user_id)
    if tx_data.get("merchant"):
        tx_data["merchant"] = encrypt_user_data(tx_data["merchant"], user_id)

    db_transaction = Transaction(**tx_data, user_id=user_id)
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    _decrypt_transaction(db_transaction, user_id)
    return db_transaction


def get_transactions_by_account(db: Session, account_id: uuid.UUID):
    transactions = db.query(Transaction).filter(Transaction.account_id == account_id).all()
    for tx in transactions:
        _decrypt_transaction(tx, tx.user_id)
    return transactions


def get_transactions_by_user(db: Session, user_id: str):
    transactions = db.query(Transaction).filter(Transaction.user_id == user_id).all()
    for tx in transactions:
        _decrypt_transaction(tx, user_id)
    return transactions


def get_user_transactions_last_30_days(db: Session, user_id: str):
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    transactions = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id, Transaction.date >= thirty_days_ago)
        .all()
    )
    for tx in transactions:
        _decrypt_transaction(tx, user_id)
    return transactions


def get_total_spending_for_category_and_month(
    db: Session, user_id: str, category: str, year: int, month: int
) -> float:
    start_of_month = datetime(year, month, 1)
    # Handle end of month for filtering
    if month == 12:
        end_of_month = datetime(year + 1, 1, 1) - timedelta(microseconds=1)
    else:
        end_of_month = datetime(year, month + 1, 1) - timedelta(microseconds=1)

    total_spent = (
        db.query(func.sum(Transaction.amount))
        .filter(
            Transaction.user_id == user_id,
            Transaction.category == category,
            Transaction.date >= start_of_month,
            Transaction.date <= end_of_month,
            Transaction.type
            == "DEBIT",  # Only consider debit transactions for spending
        )
        .scalar()
    )
    return total_spent if total_spent is not None else 0.0


def get_monthly_spending_history(
    db: Session, user_id: str, category: str, months: int = 12
):
    """
    Computes the average and minimum monthly spending for a category over a given period.
    """
    today = datetime.utcnow().date()
    monthly_spends = []
    processed_months = set()

    for i in range(months):
        # Go back month by month
        target_date = today - timedelta(days=i * 30)  # Approximate
        year, month = target_date.year, target_date.month

        if (year, month) not in processed_months:
            processed_months.add((year, month))
            monthly_spend = get_total_spending_for_category_and_month(
                db, user_id, category, year, month
            )
            # Only include months where there was spending, to get a realistic 'min_spend'
            if monthly_spend > 0:
                monthly_spends.append(monthly_spend)

    # We need at least two data points to find a meaningful reduction
    if len(monthly_spends) < 2:
        return {"avg_spend": 0, "min_spend": 0}

    avg_spend = sum(monthly_spends) / len(monthly_spends)
    min_spend = min(monthly_spends)

    return {"avg_spend": avg_spend, "min_spend": min_spend}
