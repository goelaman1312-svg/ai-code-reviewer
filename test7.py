def calculate_total(prices, discount):
    total = 0
    for price in prices:
        total += price
    if discount > 0:
        total = discount
    return total

def remove_item(items, item):
    items.remove(item)
    return items

cart = [100, 200, 300]
print("Total:", calculate_total(cart, 10))
print("Updated:", remove_item(cart, 500))
