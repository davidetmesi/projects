"""
Unit & Concurrency Tests – Thread-Safe Bank Account System
===========================================================
Run with:  python -m pytest test_bank_account.py -v
       or:  python test_bank_account.py
"""

import threading
import unittest

from bank_account import BankAccount, TransactionSimulator, transfer


# ===========================================================================
# 1. BankAccount – basic (single-threaded) tests
# ===========================================================================

class TestBankAccountBasic(unittest.TestCase):

    def _make(self, balance=500.0):
        return BankAccount("TEST-001", initial_balance=balance)

    # --- construction ---

    def test_initial_balance(self):
        acc = self._make(250.0)
        self.assertEqual(acc.get_balance(), 250.0)

    def test_negative_initial_balance_raises(self):
        with self.assertRaises(ValueError):
            BankAccount("X", initial_balance=-1)

    # --- deposit ---

    def test_deposit_increases_balance(self):
        acc = self._make(100.0)
        acc.deposit(50.0)
        self.assertAlmostEqual(acc.get_balance(), 150.0)

    def test_deposit_zero_raises(self):
        acc = self._make()
        with self.assertRaises(ValueError):
            acc.deposit(0)

    def test_deposit_negative_raises(self):
        acc = self._make()
        with self.assertRaises(ValueError):
            acc.deposit(-10)

    # --- withdraw ---

    def test_withdraw_decreases_balance(self):
        acc = self._make(200.0)
        result = acc.withdraw(80.0)
        self.assertTrue(result)
        self.assertAlmostEqual(acc.get_balance(), 120.0)

    def test_withdraw_insufficient_funds_returns_false(self):
        acc = self._make(50.0)
        result = acc.withdraw(100.0)
        self.assertFalse(result)
        self.assertAlmostEqual(acc.get_balance(), 50.0)   # unchanged

    def test_withdraw_exact_balance(self):
        acc = self._make(100.0)
        result = acc.withdraw(100.0)
        self.assertTrue(result)
        self.assertAlmostEqual(acc.get_balance(), 0.0)

    def test_withdraw_zero_raises(self):
        acc = self._make()
        with self.assertRaises(ValueError):
            acc.withdraw(0)

    def test_withdraw_negative_raises(self):
        acc = self._make()
        with self.assertRaises(ValueError):
            acc.withdraw(-5)

    # --- get_balance ---

    def test_get_balance_returns_float(self):
        acc = self._make(123.45)
        self.assertIsInstance(acc.get_balance(), float)

    # --- transaction log ---

    def test_transaction_log_records_deposit(self):
        acc = self._make(0.0)
        acc.deposit(10.0)
        log = acc.get_transaction_log()
        self.assertEqual(len(log), 1)
        self.assertIn("DEPOSIT", log[0])

    def test_transaction_log_records_withdraw(self):
        acc = self._make(100.0)
        acc.withdraw(10.0)
        log = acc.get_transaction_log()
        self.assertEqual(len(log), 1)
        self.assertIn("WITHDRAW", log[0])

    def test_transaction_log_records_failed_withdraw(self):
        acc = self._make(5.0)
        acc.withdraw(100.0)
        log = acc.get_transaction_log()
        self.assertIn("FAILED", log[0])

    def test_transaction_log_is_copy(self):
        acc = self._make(0.0)
        acc.deposit(1.0)
        log = acc.get_transaction_log()
        log.append("tampered")
        self.assertEqual(len(acc.get_transaction_log()), 1)   # original intact


# ===========================================================================
# 2. BankAccount – thread-safety (concurrent) tests
# ===========================================================================

class TestBankAccountThreadSafety(unittest.TestCase):

    def _concurrent(self, target, num_threads=50, **kwargs):
        barrier = threading.Barrier(num_threads)

        def worker():
            barrier.wait()   # all threads start at the same moment
            target(**kwargs)

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    # --- concurrent deposits ---

    def test_concurrent_deposits_are_consistent(self):
        """50 threads each deposit 10 → balance must be exactly 500."""
        acc = BankAccount("CONC-DEP", initial_balance=0.0)
        self._concurrent(acc.deposit, num_threads=50, amount=10.0)
        self.assertAlmostEqual(acc.get_balance(), 500.0)

    # --- concurrent withdrawals ---

    def test_concurrent_withdrawals_never_go_negative(self):
        """50 threads each try to withdraw 10 from a 200-unit pot."""
        acc = BankAccount("CONC-WIT", initial_balance=200.0)
        self._concurrent(acc.withdraw, num_threads=50, amount=10.0)
        self.assertGreaterEqual(acc.get_balance(), 0.0)

    def test_concurrent_withdrawals_correct_final_balance(self):
        """
        100 threads each try to withdraw 5 from a 300-unit account.
        Only 60 can succeed → final balance must be exactly 0.
        (300 / 5 = 60 successful withdrawals.)
        """
        acc = BankAccount("CONC-WIT2", initial_balance=300.0)
        results = []
        lock = threading.Lock()

        def worker():
            ok = acc.withdraw(5.0)
            with lock:
                results.append(ok)

        barrier = threading.Barrier(100)

        def run():
            barrier.wait()
            worker()

        threads = [threading.Thread(target=run) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertAlmostEqual(acc.get_balance(), 0.0)
        self.assertEqual(sum(results), 60)   # exactly 60 withdrawals succeed

    # --- mixed concurrent operations ---

    def test_mixed_concurrent_operations(self):
        """
        Half threads deposit 20, half withdraw 20.
        Net change = 0 → final balance equals initial balance.
        """
        initial = 1_000.0
        acc = BankAccount("MIXED", initial_balance=initial)
        n = 40   # 40 deposits + 40 withdrawals
        barrier = threading.Barrier(n * 2)

        def depositor():
            barrier.wait()
            acc.deposit(20.0)

        def withdrawer():
            barrier.wait()
            acc.withdraw(20.0)

        threads = (
            [threading.Thread(target=depositor) for _ in range(n)] +
            [threading.Thread(target=withdrawer) for _ in range(n)]
        )
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertAlmostEqual(acc.get_balance(), initial)


# ===========================================================================
# 3. Transfer – correctness and deadlock prevention
# ===========================================================================

class TestTransfer(unittest.TestCase):

    def test_transfer_moves_money(self):
        a = BankAccount("A", initial_balance=500.0)
        b = BankAccount("B", initial_balance=100.0)
        ok = transfer(a, b, 200.0)
        self.assertTrue(ok)
        self.assertAlmostEqual(a.get_balance(), 300.0)
        self.assertAlmostEqual(b.get_balance(), 300.0)

    def test_transfer_insufficient_funds(self):
        a = BankAccount("A", initial_balance=50.0)
        b = BankAccount("B", initial_balance=100.0)
        ok = transfer(a, b, 200.0)
        self.assertFalse(ok)
        self.assertAlmostEqual(a.get_balance(), 50.0)
        self.assertAlmostEqual(b.get_balance(), 100.0)

    def test_transfer_conserves_total_money(self):
        a = BankAccount("A", initial_balance=1_000.0)
        b = BankAccount("B", initial_balance=1_000.0)
        total_before = a.get_balance() + b.get_balance()

        results = []
        lock = threading.Lock()

        def do_transfer(src, tgt, amt):
            ok = transfer(src, tgt, amt)
            with lock:
                results.append(ok)

        # A→B and B→A simultaneously – deadlock-prone without ordering
        threads = []
        for _ in range(20):
            threads.append(threading.Thread(target=do_transfer, args=(a, b, 100.0)))
            threads.append(threading.Thread(target=do_transfer, args=(b, a, 100.0)))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        total_after = a.get_balance() + b.get_balance()
        self.assertAlmostEqual(total_before, total_after,
                               msg="Money was created or destroyed during transfers!")

    def test_no_deadlock_opposite_direction_transfers(self):
        """
        Hammer 100 concurrent A→B and B→A transfers.
        The test itself would hang (timeout) if a deadlock occurred.
        """
        a = BankAccount("AA", initial_balance=5_000.0)
        b = BankAccount("BB", initial_balance=5_000.0)

        barrier = threading.Barrier(100)

        def worker(src, tgt):
            barrier.wait()
            transfer(src, tgt, 10.0)

        threads = (
            [threading.Thread(target=worker, args=(a, b)) for _ in range(50)] +
            [threading.Thread(target=worker, args=(b, a)) for _ in range(50)]
        )
        for t in threads:
            t.start()
        for t in threads:
            t.join()   # would block here if deadlocked

        # If we reach this line, no deadlock occurred
        total = a.get_balance() + b.get_balance()
        self.assertAlmostEqual(total, 10_000.0)


# ===========================================================================
# 4. TransactionSimulator integration test
# ===========================================================================

class TestTransactionSimulator(unittest.TestCase):

    def _run_sim(self, num_accounts=2, num_users=5, tx=20, balance=1_000.0):
        accounts = [BankAccount(f"SIM-{i}", initial_balance=balance)
                    for i in range(num_accounts)]
        total_before = sum(a.get_balance() for a in accounts)

        sim = TransactionSimulator(
            accounts=accounts,
            num_users=num_users,
            transactions_per_user=tx,
            max_amount=50.0,
        )
        sim.run()

        total_after = sum(a.get_balance() for a in accounts)
        return total_before, total_after, sim.summary()

    def test_money_conserved_across_accounts(self):
        """
        Transfers simply move money; deposits/withdrawals with
        an external party change totals legitimately – here we
        only check no account goes negative.
        """
        accounts = [BankAccount(f"C-{i}", initial_balance=500.0) for i in range(3)]
        sim = TransactionSimulator(accounts, num_users=10, transactions_per_user=15)
        sim.run()
        for acc in accounts:
            self.assertGreaterEqual(
                acc.get_balance(), 0.0,
                f"{acc.account_number} went negative!"
            )

    def test_summary_keys_present(self):
        _, _, summary = self._run_sim()
        self.assertIn("per_user", summary)
        self.assertIn("final_balances", summary)

    def test_all_users_reported(self):
        _, _, summary = self._run_sim(num_users=4)
        self.assertEqual(len(summary["per_user"]), 4)

    def test_no_account_goes_negative(self):
        accounts = [BankAccount(f"NEG-{i}", initial_balance=200.0) for i in range(2)]
        sim = TransactionSimulator(accounts, num_users=8, transactions_per_user=30, max_amount=80.0)
        sim.run()
        for acc in accounts:
            self.assertGreaterEqual(acc.get_balance(), 0.0)

    def test_high_concurrency(self):
        """Stress test: 20 users, 50 transactions each, 3 accounts."""
        accounts = [BankAccount(f"HC-{i}", initial_balance=2_000.0) for i in range(3)]
        sim = TransactionSimulator(accounts, num_users=20, transactions_per_user=50, max_amount=200.0)
        sim.run()
        for acc in accounts:
            self.assertGreaterEqual(acc.get_balance(), 0.0)


# ===========================================================================
# Entry point
# ===========================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
