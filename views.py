
from audioop import reverse
from base64 import b64encode
from datetime import datetime
from email import message
import requests
import json
from multiprocessing import context
from pyexpat.errors import messages
from urllib import request, response
import uuid
from xml.dom import ValidationErr
from django.shortcuts import render,redirect,get_object_or_404
from django_daraja.mpesa.core import MpesaClient
from.forms import MpesaForm
from django.http import JsonResponse
from twilio.rest import Client
from django.forms.models import model_to_dict





# Create your views here.
from django.http import HttpResponse
from .models import Booking, Destination,Transactions,TurkBus,Bus_Route
from .forms import bookingForm
from decouple import config
from .LipaNaMpesaOnline import LipaNaMpesa



def index(request):    
    dests=Destination.objects.all()
   
    return render(request,'home.html',{
        'dests':dests,
        
    })

def checkseats(request,bus_id=None):
    if bus_id is not None:
      bus=TurkBus.objects.get(id=bus_id)
      reserved_seats = Booking.objects.filter(bus=bus).count()
      available_seats = bus.capacity - reserved_seats
      if bus.capacity==reserved_seats:
        reserved_seats=''
      bus_routes = Bus_Route.objects.filter(bus=bus)  
      return render(request, 'seats.html', {'available_seats': available_seats,'bus':bus,'bus_routes': bus_routes})
    else:
        all_buses = TurkBus.objects.all()
        bus_data = []

        for bus in all_buses:
            reserved_seats = Booking.objects.filter(bus=bus).count()
            available_seats = bus.capacity - reserved_seats
            if bus.capacity == reserved_seats:
                reserved_seats = bus.capacity
            bus_routes = Bus_Route.objects.filter(bus=bus)    
            bus_data.append({
                'bus': bus,
                'available_seats': available_seats,
                'reserved_seats': reserved_seats,
                'bus_routes': bus_routes
            })

        return render(request, 'seats.html', {'bus_data': bus_data})  

def booking(request):
     
     if request.method=='POST':
         form=bookingForm(request.POST)
         if form.is_valid():
            '''instance = form.save(commit=False)
            bus_number = form.cleaned_data['bus']
            turkbus_instance = get_object_or_404(TurkBus, bus_number=bus_number)

            instance.bus = turkbus_instance
            instance.save()'''
            form.save()
            return redirect('transaction')     
           
     else:
            # Display the booking form
        form = bookingForm()
        '''bus_numbers = TurkBus.objects.values_list('bus_number', flat=True).distinct()
        bus_choices = [(number,number) for number in bus_numbers]
        form=bookingForm()
        print(bus_choices)  
        form.fields['bus'].choices = bus_choices'''
        
        


     return render(request, 'list.html', {'form': form})

def transaction(request):
    global amount
    global price
    latest_booking = Booking.objects.last()

    if request.method=='POST':
    
       seat_number=request.POST.get('seat_number')
       source=request.POST.get('From')
       dest=request.POST.get('To')
       phone_number=request.POST.get('phone_number')

       if source=='Lodwar' and dest=='Eldoret'or source=='Eldoret'and dest=='Lodwar':
           price=1500
           amount=int(seat_number) * price
       elif source=='Kitale'and dest=='Lodwar'or source=='Lodwar'and dest=='Kitale':
           price=1200
           amount=int(seat_number) * price
       elif source=="Kitale" and dest=="Eldoret"or source=="Eldoret"and dest=="Kitale":  
            price=300
            amount=int(seat_number) * price
       else:
           
           return  redirect('mpesa.html')

       request.session['phone_number'] = phone_number
       request.session['amount'] = amount
       #checkout_request_id = uuid.uuid4().hex
   
       new_transactions=Transactions(amount=amount,phone_number=phone_number)
       new_transactions.save()
              
       return render(request,'transaction.html',{'amount':str(amount),'update_ptext': True,'seat_number': seat_number,
                'source': source,
                'dest': dest,
                'phone_number': phone_number,
                'latest_booking':latest_booking})
    return render(request,'transaction.html',{'latest_booking':latest_booking})        

def mpesa(request):
    amount=request.session.get('amount', 0)
    phone_number = request.session.get('phone_number', '')
    
    if request.method=="POST":
    
      form = MpesaForm(request.POST)
      if form.is_valid():
            phone_number = form.cleaned_data['phone_number']
            amount = form.cleaned_data['amount']
            account_reference = 'Turk Reef Bus'
            transaction_desc = 'Description'
            callback_url = 'https://en60o6vqxhcnk.x.pipedream.net'
            
            cl=MpesaClient()

            response=cl.stk_push(phone_number, amount, account_reference, transaction_desc, callback_url)
            
            if response:
                response_data = json.loads(response.content)
                merchant_request_id = response_data.get('MerchantRequestID','')
                checkout_request_id = response_data.get('CheckoutRequestID','')
                transaction_id = response_data.get('ResponseCode', '')

                
                request.session['checkout_request_id'] = checkout_request_id
                request.session['merchant_request_id'] = merchant_request_id
                status_code=response.status_code

                Transactions.objects.create(
                    amount=amount,
                    phone_number=form.cleaned_data['phone_number'],
                    checkout_request_id=checkout_request_id
                )
                
                 
            '''return render(request, 'payment_status.html', {
                    'merchant_request_id': merchant_request_id,
                    'checkout_request_id': checkout_request_id,
                    'transaction_id': transaction_id,
                    'status_code': status_code,
                    'response_data':response_data
                })'''
      
    else:
        form = MpesaForm(initial={'phone_number':phone_number, 'amount': amount})
        
    return render(request, 'mpesa.html', {'form': form,'amount':amount})

def stk_push_callback(request):
      latest_booking = Booking.objects.last()
      name=latest_booking.passenger_name
      From=latest_booking.From
      To=latest_booking.To
      date=latest_booking.date_of_travel
      #phone_number = latest_booking.phone_number.as_e164()
      checkout_request_id = request.session.get('checkout_request_id', '')
      #transaction=checkout_request_id
      merchant_request_id = request.session.get('merchant_request_id', '')
      print(merchant_request_id)
      cl=MpesaClient()
      access_token=cl.access_token()
      
      short_code = '174379'
      time_now = datetime.now().strftime("%Y%m%d%H%I%S")
      pass_key='bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919'
      s= short_code + pass_key + time_now
      encoded = b64encode(s.encode('utf-8')).decode('utf-8')

    
    # M-Pesa API endpoint for transaction status
      endpoint = 'https://sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query'
    
      headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
      payload = {
            'BusinessShortCode': short_code,
            'Password': encoded,  
            'Timestamp': time_now, 
            'TransactionType': 'TransactionStatusQuery',
            'CheckoutRequestID':checkout_request_id

        }
        
      response = requests.post(endpoint, json=payload, headers=headers)
       
      json_response = json.loads(response.text)
      print(json_response)
      #result=response.json()
      result_code=json_response.get('ResultCode')
      res_desc=json_response.get('ResultDesc')
      message = f"Hello {name}, your trip from {From} to {To} on { date } has been booked successfully"
      if 'ResultCode' in json_response and json_response['ResultCode'] == '0':
          
          #send_sms_alert(message)
          transaction = Transactions.objects.get(checkout_request_id=checkout_request_id)  
          transaction.is_finished = True
          transaction.is_successful = True
          transaction.receipt_no=merchant_request_id
          transaction.save()
       
          return render(request,'payment_status.html',{'res_desc':res_desc})
      elif 'ResultCode' in json_response and json_response['ResultCode']=='1032':
          #send_sms_alert(message)
          transaction = Transactions.objects.get(checkout_request_id=checkout_request_id)  
          transaction.is_finished = True
          transaction.is_successful = False
          transaction.receipt_no=merchant_request_id
          transaction.save()
          return render(request,'payment_cancel.html',{'res_desc':res_desc})  
      else:
          #send_sms_alert(message)
          transaction = Transactions.objects.get(checkout_request_id=checkout_request_id)  # Replace with your actual lookup criteria
          transaction.is_finished = True
          transaction.is_successful = False
          transaction.receipt_no=merchant_request_id
          
          transaction.save()
      
          return render(request,'payment_fail.html',{'res_desc':res_desc})

      
def send_sms_alert(message):
        latest_booking=Booking.objects.last()
        phone_number=latest_booking.phone_number
        account_sid = 'AC6ab95cd3eae0180dab5db66f080a0324'
        auth_token = 'b750b9c491a9cb89af466670563a8eb1'
        twilio_phone_number = '+13343779191'
        recipient_phone_number = str(phone_number)

    # Create a Twilio client
        client = Client(account_sid, auth_token)

    # Send SMS
        client.messages.create(
        body=message,
        from_=twilio_phone_number,
        to=recipient_phone_number
    )
    
