import random

def make_captcha():
    a = random.randint(2, 15)
    b = random.randint(2, 15)
    op = random.choice(["+", "-", "*"])
    if op == "+":
        return f"{a} + {b}", a + b
    elif op == "-":
        return f"{a} - {b}", a - b
    else:
        return f"{a} × {b}", a * b
