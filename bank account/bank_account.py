"""
Thread-Safe Bank Account System
================================
Implements BankAccount with full thread safety, TransactionSimulator
for concurrent transaction testing, and deadlock-safe transfers.
"""

import threading
import time
import random
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(threadName)s] %(message)s"
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# BankAccount
# ---------------------------------------------------------------------------

class BankAccount:
    """A thread-safe bank account using a reentrant lock."""

    def __init__(self, account_number: str, initial_balance: float = 0.0):
        if initial_balance < 0:
            raise ValueError("Initial balance cannot be negative.")
        self.account_number = account_number
        self._balance = initial_balance
        self._lock = threading.RLock()          # reentrant – safe for nested calls
        self._transaction_log: list[str] = []

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def deposit(self, amount: float) -> bool:
        """Add *amount* to the balance. Returns True on success."""
        if amount <= 0:
            raise ValueError(f"Deposit amount must be positive, got {amount}.")
        with self._lock:
            self._balance += amount
            self._log(f"DEPOSIT  +{amount:.2f}  → balance={self._balance:.2f}")
            return True

    def withdraw(self, amount: float) -> bool:
        """
        Deduct *amount* from the balance.
        Returns True on success, False if insufficient funds.
        """
        if amount <= 0:
            raise ValueError(f"Withdrawal amount must be positive, got {amount}.")
        with self._lock:
            if self._balance < amount:
                self._log(f"WITHDRAW FAILED  -{amount:.2f}  (insufficient funds, balance={self._balance:.2f})")
                return False
            self._balance -= amount
            self._log(f"WITHDRAW -{amount:.2f}  → balance={self._balance:.2f}")
            return True

    def get_balance(self) -> float:
        """Return the current balance (thread-safe snapshot)."""
        with self._lock:
            return self._balance

    def get_transaction_log(self) -> list[str]:
        """Return a copy of the transaction log."""
        with self._lock:
            return list(self._transaction_log)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _log(self, message: str) -> None:
        entry = f"[{self.account_number}] {message}"
        self._transaction_log.append(entry)
        logger.debug(entry)

    def __repr__(self) -> str:
        return f"BankAccount(account_number={self.account_number!r}, balance={self._balance:.2f})"


# ---------------------------------------------------------------------------
# Deadlock-safe transfer utility
# ---------------------------------------------------------------------------

def transfer(source: BankAccount, target: BankAccount, amount: float) -> bool:
    """
    Transfer *amount* from *source* to *target* without risk of deadlock.

    Deadlock prevention strategy: always acquire locks in a globally
    consistent order (sorted by account_number).  This breaks the
    circular-wait condition that would otherwise cause a deadlock when
    two threads try to transfer in opposite directions simultaneously.
    """
    # Determine a canonical lock-acquisition order
    first, second = sorted([source, target], key=lambda a: a.account_number)

    with first._lock:
        with second._lock:
            if source._balance < amount:
                logger.debug(
                    "[TRANSFER] Insufficient funds in %s (%.2f < %.2f)",
                    source.account_number, source._balance, amount
                )
                return False
            source._balance -= amount
            target._balance += amount
            source._log(f"TRANSFER OUT -{amount:.2f} → {target.account_number}  balance={source._balance:.2f}")
            target._log(f"TRANSFER IN  +{amount:.2f} ← {source.account_number}  balance={target._balance:.2f}")
            return True


# ---------------------------------------------------------------------------
# TransactionSimulator
# ---------------------------------------------------------------------------

class TransactionSimulator:
    """
    Simulates multiple users performing concurrent deposits and
    withdrawals (and optional cross-account transfers) on shared accounts.
    """

    def __init__(self, accounts: list[BankAccount], num_users: int = 5,
                 transactions_per_user: int = 10, max_amount: float = 100.0):
        self.accounts = accounts
        self.num_users = num_users
        self.transactions_per_user = transactions_per_user
        self.max_amount = max_amount

        self._threads: list[threading.Thread] = []
        self._results: dict[str, list] = {}          # user → list of bool results
        self._results_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Launch all user threads and wait for them to finish."""
        self._threads.clear()
        self._results.clear()

        for i in range(self.num_users):
            user_name = f"User-{i + 1}"
            t = threading.Thread(
                target=self._user_session,
                args=(user_name,),
                name=user_name,
                daemon=False,
            )
            self._threads.append(t)

        logger.info("=== Simulation START – %d users, %d tx each ===",
                    self.num_users, self.transactions_per_user)
        for t in self._threads:
            t.start()
        for t in self._threads:
            t.join()
        logger.info("=== Simulation DONE ===")

    def summary(self) -> dict:
        """Return a dict with per-user results and final balances."""
        with self._results_lock:
            per_user = {u: {"total": len(r), "success": sum(r)} for u, r in self._results.items()}
        return {
            "per_user": per_user,
            "final_balances": {acc.account_number: acc.get_balance() for acc in self.accounts},
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _user_session(self, user: str) -> None:
        results = []
        for _ in range(self.transactions_per_user):
            account = random.choice(self.accounts)
            amount = round(random.uniform(1.0, self.max_amount), 2)
            action = random.choice(["deposit", "withdraw", "transfer"])

            if action == "deposit":
                ok = account.deposit(amount)
            elif action == "withdraw":
                ok = account.withdraw(amount)
            else:   # transfer between two distinct accounts
                if len(self.accounts) < 2:
                    ok = account.deposit(amount)   # fallback
                else:
                    other = random.choice([a for a in self.accounts if a is not account])
                    ok = transfer(account, other, amount)

            results.append(ok)
            # Small random sleep to increase thread interleaving
            time.sleep(random.uniform(0.0, 0.005))

        with self._results_lock:
            self._results[user] = results


# ---------------------------------------------------------------------------
# Quick smoke-test (run directly)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    acc_a = BankAccount("ACC-001", initial_balance=1_000.0)
    acc_b = BankAccount("ACC-002", initial_balance=1_000.0)
    total_before = acc_a.get_balance() + acc_b.get_balance()

    sim = TransactionSimulator(
        accounts=[acc_a, acc_b],
        num_users=8,
        transactions_per_user=20,
        max_amount=150.0,
    )
    sim.run()

    s = sim.summary()
    total_after = sum(s["final_balances"].values())

    print("\n─── Summary ────────────────────────────────")
    for user, stats in s["per_user"].items():
        print(f"  {user}: {stats['success']}/{stats['total']} successful")
    print(f"\n  Final balances : {s['final_balances']}")
    print(f"  Total before   : {total_before:.2f}")
    print(f"  Total after    : {total_after:.2f}")
    print(f"  Money conserved: {total_before == total_after}")
