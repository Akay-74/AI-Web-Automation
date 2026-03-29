import pytest
from app.services.agent.validator import ResultValidator

def test_gpu_validation_exact_match():
    goal = "Find cheapest RTX 4060 laptop"
    validator = ResultValidator(goal)
    
    assert validator.constraints.get("gpu") == "RTX 4060", "Must parse GPU correctly"
    
    # Valid item
    item = {"name": "ASUS TUF Gaming A15", "gpu": "NVIDIA GeForce RTX 4060 8GB", "price": 999.00}
    result = validator.validate_item(item)
    assert result["is_valid"] is True
    assert "✓ Contains RTX 4060" in result["validation_reason"]

def test_gpu_validation_rejects_wrong_gpu():
    goal = "Find cheapest RTX 4060 laptop"
    validator = ResultValidator(goal)
    
    # Rejected items
    item1 = {"name": "Lenovo Legion 5", "specs": {"gpu": "RTX 4050 6GB"}, "price": 899.00}
    result1 = validator.validate_item(item1)
    assert result1["is_valid"] is False
    assert "✗ Contains wrong GPU: RTX 4050" in result1["validation_reason"]
    
    item2 = {"name": "Acer Nitro V", "gpu": "RTX 3050 Ti", "price": 750.00}
    result2 = validator.validate_item(item2)
    assert result2["is_valid"] is False
    assert "✗ Contains wrong GPU: RTX 3050" in result2["validation_reason"]

def test_price_constraint():
    goal = "Find RTX 4060 under $1000"
    validator = ResultValidator(goal)
    
    assert validator.constraints.get("max_price") == 1000.0, "Must parse price constraint"
    
    # Valid price
    item_good = {"name": "Laptop A", "gpu": "RTX 4060", "price": 999.99}
    assert validator.validate_item(item_good)["is_valid"] is True
    
    # Exceeds price
    item_bad = {"name": "Laptop B", "gpu": "RTX 4060", "price": 1050.00}
    result_bad = validator.validate_item(item_bad)
    assert result_bad["is_valid"] is False
    assert "exceeds" in result_bad["validation_reason"]

def test_brand_constraint():
    goal = "Find acer rtx 4060 laptop"
    validator = ResultValidator(goal)
    
    assert validator.constraints.get("brand") == "acer"
    
    item = {"name": "Acer Nitro", "gpu": "RTX 4060"}
    res = validator.validate_item(item)
    assert res["is_valid"] is True
    assert "Brand matches" in res["validation_reason"]
