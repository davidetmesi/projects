# CartSystem — Python (VS Code)

A Python translation of the CartSystem VB.NET solution, implementing four
design patterns required for the e-Portfolio assignment.

## Project Structure

```
CartSystem/
├── domain/
│   └── models.py          # Entities (Product, Cart, CartItem) + abstract interfaces
├── core/
│   ├── patterns.py        # Strategy, Decorator, Visitor, Abstract Factory
│   └── infrastructure.py  # In-memory repository & console notification
├── tests/
│   └── test_cart_system.py # Unit tests with mocking (unittest + MagicMock)
├── demo/
│   └── main.py            # End-to-end walkthrough of all patterns
└── .vscode/
    ├── launch.json        # Run/debug configurations
    └── settings.json      # Python path settings
```

## Setup (VS Code)

1. Open the `CartSystem/` folder in VS Code:
   `File → Open Folder → select CartSystem`

2. Select Python interpreter (Python 3.10+ recommended):
   `Ctrl+Shift+P → Python: Select Interpreter`

3. No external packages required — uses only the Python standard library.

## Running

### Demo (all patterns)
```bash
# From inside the CartSystem/ folder:
python demo/main.py
```

### Tests
```bash
# unittest (built-in)
python -m unittest discover -s tests -v

# or pytest (install first: pip install pytest)
pytest tests/ -v
```

### VS Code Run & Debug panel
Use the pre-configured launch targets:
- **Run Demo** — executes `demo/main.py`
- **Run All Tests** — runs unittest discovery
- **Run Tests (pytest)** — runs pytest

## Design Patterns

| Pattern | File | Purpose |
|---|---|---|
| Strategy | `core/patterns.py` | Interchangeable pricing (Standard, Seasonal, Bulk, Loyalty) |
| Decorator | `core/patterns.py` | Layered cart service (Logging, Security, Audit) |
| Visitor | `core/patterns.py` | Analytics & Tax reporting separated from domain |
| Abstract Factory | `core/patterns.py` | Pluggable AI/Payment families (Cloud vs Local) |
