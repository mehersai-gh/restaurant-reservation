import razorpay

RAZORPAY_KEY_ID="rzp_test_PWBcXpVD7UlUNz"
RAZORPAY_KEY_SECRET="BcgNENV5npJLR5VWE3xIGXZz"

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

def create_order(amount, currency="INR", receipt=None):
    """Creates an order with Razorpay"""
    data = {
        "amount": amount * 100,  # Razorpay accepts amount in paisa
        "currency": currency,
        "receipt": receipt,
        "payment_capture": 1  # Auto capture payment
    }
    order = razorpay_client.order.create(data)
    return order
