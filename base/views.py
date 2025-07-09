import uuid
from django.shortcuts import render , redirect
from .models import Transaction 
import requests
from django.conf import settings
from . forms import RegistrationForm
from django.contrib import messages




def checkout(request):
    tx_ref = f"tx-{uuid.uuid4()}"
    amount = 200

    Transaction.objects.create(
        ref=tx_ref, 
        amount=amount, 
        customer_name=request.POST.get("customer_name", "anonymous"),  # Example name, can be dynamic
        customer_email=request.POST.get("customer_email", "anonymous@example.com"),  # Example email, can be dynamic
        customer_phone=request.POST.get("customer_phone", "0000000000"),  # Example phone, can be dynamic
        currency='NGN'  
    )

 

    context = {
        "public_key": "FLWPUBK-b8889e6d268502fac038208fbf6bc99c-X",
        "tx_ref": tx_ref,
        "amount": amount,
        "currency": "NGN",
        "redirect_url": "https://f5d1efb8682f.ngrok-free.app/payment_callback",

    }

    return render(request, "base/checkout.html", context)



def payment_callback(request):
    tx_ref = request.GET.get('tx_ref')
    status = request.GET.get('status')
    transaction_id = request.GET.get('transaction_id')

    print("Callback received:", tx_ref, status, transaction_id)

    if not tx_ref or not status or not transaction_id:
        messages.error(request, "Invalid payment details.")
        return redirect('checkout')

    try:
        transaction = Transaction.objects.get(ref=tx_ref)
    except Transaction.DoesNotExist:
        messages.error(request, "Transaction not found.")
        return redirect('checkout')

    if status in ['successful', 'completed']:
        url = f"https://api.flutterwave.com/v3/transactions/{transaction_id}/verify"
        headers = {"Authorization": f"Bearer {settings.FLW_SECRET_KEY}"}
        response = requests.get(url, headers=headers)
        data = response.json()

        if (
            data.get('status') == 'success' and
            data['data'].get('status') == 'successful' and
            float(data['data'].get('amount')) == float(transaction.amount)
        ):
            transaction.flutterwave_transaction_id = transaction_id
            transaction.status = 'paid'
            transaction.save()

            # Store the payment verification status in the session
            request.session['payment_verified'] = True

            messages.success(request, "Payment successful!")
            return redirect('register')

    messages.error(request, "Payment was not successful or verification failed.")
    return redirect('checkout')




def register(request):
    
    if not request.session.get('payment_verified'):
        messages.error(request, "Please make payment before registering.")
        return redirect('checkout')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()


            request.session.pop('payment_verified', None)

            messages.success(request, "Registration completed successfully!")
            return redirect('completed')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = RegistrationForm()

    return render(request, 'base/register.html', {'form': form})


        
def completed(request):
    return render(request, 'base/completed.html')
