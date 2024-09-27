import requests
import json
import uuid
import os
import time

# Request Network API key from environement variable 
API_KEY = os.getenv("RequestNetwork_API_KEY")

# Example payment receiver wallet address
paymentReceiverAddress= os.getenv("paymentReceiverAddress")

# Base URL used for the request network POST / GET methods 
BASE_URL = "http://localhost:3000/"

# Invoice creation access point
InvoiceEndpoint = f"{BASE_URL}invoices"

HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": f"{API_KEY}"
}


def GeneratePayload(clientInfo, currency, price, serviceName = None): 
    """
    GeneratePayload
    ---------------
    Generates a payload (dictionary) for invoice creation with the Request Network API. 
    This function prepares the necessary and mandatory parameters required to generate an invoice.

    Parameters
    ----------
    clientInfo : dict
        Dictionary containing the client's information, including the email address and the identity address.
        Example: {"email": "client@example.com"}
    currency : str
        The currency of the invoice. Can be 'ETH-sepolia' or a custom currency. 
        Currently, only 'ETH-sepolia' is supported (in wei).
    price : float
        The amount in the specified currency required to deliver the service.
    serviceName : str, optional
        A short description of the service being invoiced. If not provided, defaults to 'AI Haiku Service'.
    
    Returns
    -------
    dict
        A dictionary (`invoice_payload`) containing all the necessary fields for invoice creation, 
        ready to be sent to the Request Network API.

    Notes
    -----
    - The `price` is converted into Wei (1 ETH = 10^18 Wei).
    - The function generates a unique invoice number using UUID.
    - The default currency is 'ETH-sepolia', and the service name defaults to 'AI Haiku Service' if none is provided.
    - The buyer's email is taken from the `clientInfo` dictionary, while other details (such as the address) are commented out for potential customization.
    - The payment address is predefined and set in the `paymentReceiverAddress` variable.

    Example
    -------
    invoice_payload = GeneratePayload(
        clientInfo={"email": "client@example.com"},
        currency="ETH-sepolia",
        price=0.01,
        serviceName="Consulting Service"
    )
    """
    invoice_payload = {
        "payerAddress": clientInfo["identity-address"],  # Adress which will receive the payment
        "contentdata": {
            "invoiceItems": [
                {
                    "currency": currency or "ETH-sepolia",  #  (SepoliaETH)
                    "name": serviceName or "AI Haiku Service",  # Nom du service
                    "quantity": 1,  # Quantité de service
                    "unitPrice": str(int(price * 10**18)),  # unit price in Wei
                }
            ],
            "invoiceNumber":  f"{uuid.uuid4()}",  # unique invoice number
            "buyerInfo": {
                # "address": {
                #     "streetAddress": "123 Blockchain Lane",
                #     "extendedAddress": "",
                #     "city": "Cryptoville",
                #     "postalCode": "10001",
                #     "region": "Crypto State",
                #     "country": "US"
                # },
                "email": clientInfo["email"],
                #"firstName": clientInfo["firstName"],
                # "lastName": "Doe",
            },
        },
        "paymentAddress": paymentReceiverAddress,  # Adress which will receive the payment
        "expectedAmount": str(int(price * 10**18)),
        "currency": "ETH-sepolia", 
    }

    return invoice_payload

     
def Send_invoice(invoice_payload):
    """
    Send_invoice
    ------------
    Function to deploy an invoice using the Request Network API.

    Parameters
    ----------
    invoice_payload : dict
        A dictionary containing the payload of the invoice. It must follow the format required by the Request Network API.
    
    Returns
    -------
    tuple or None
        On success, returns a tuple (str, str) containing:
            - The URL for the client to sign up and pay the invoice.
            - The invoice ID.
        If the invoice creation fails, returns None.
    
    Notes
    -----
    The function first sends a POST request to create an off-chain invoice. If successful, it retrieves the `requestId`
    and sends another request to convert the off-chain invoice to an on-chain request. 
    If any of the requests fail, the function returns None.
    """
    # Post request for  Off-Chain Invoice Creation 

    print(invoice_payload)
    response = requests.post(InvoiceEndpoint, headers=HEADERS, data=json.dumps(invoice_payload))
        

    if response.status_code == 201:
        response_data = response.json()
        requestId=response_data.get("id")
        paymentReference=response_data.get("paymentReference")
        return 'https://invoicing.request.network/', requestId, paymentReference;
    if response.status_code == 400:
        error_message = response.json().get("error", "Unknown error")
        print(f"Error 400: {error_message}")
        return None, None, None
    else:
        return None,None,None #f"Error during the creation of the invoice, please check the inputs. Error was : {response.content}"


def GenerateAndSendInvoice(clientInfo_Email, clientInfo_identity_address, currency, price, serviceName, autoPayment):
    """
    GenerateAndSendInvoice
    ----------------------
    Main function to generate and send an invoice using the Request Network API. 
    It creates the payload, sends the invoice, and returns either a payment reference for automated payment 
    or a URL for manual payment, depending on the autoPayment flag.

    Parameters
    ----------
    clientInfo_Email : str
        The email address of the client to whom the invoice will be sent.
    clientInfo_identity_address : str
        The buyer identity  / wallet address
    currency : str
        The currency in which the invoice is issued (e.g., 'ETH-sepolia'). Currently, only 'ETH-sepolia' is supported (in wei).
    price : float
        The amount of the invoice, in the specified currency, required for the service.
    serviceName : str or None
        A brief description of the service. If None, a default service name is used.
    autoPayment : bool
        If True, the function will generate and return a payment reference for automated payment by AI.
        If False, it will return a URL for manual payment.

    Returns
    -------
    str
        A message detailing either the payment reference for automated payment or a URL for manual payment.
        The message also includes the invoice ID, which can be used to track the status of the payment.

    Notes
    -----
    - If any mandatory information (email, currency, or price) is missing, the function returns an error message.
    - The function first generates the invoice payload using `GeneratePayload`, then sends the invoice using `Send_invoice`.
    - If `autoPayment` is True, a payment reference is generated using `computePaymentReference` and returned.
    - If `autoPayment` is False, a manual payment URL is returned.

    Example
    -------
    result = GenerateAndSendInvoice(
        clientInfo_Email="client@example.com",
        currency="ETH-sepolia",
        price=0.05,
        serviceName="Web Development Service",
        autoPayment=True
    )
    print(result)
    """
    clientInfo = {}
    if clientInfo_Email is None :
        return "Email of the client is missing"
    else: 
        clientInfo["email"]  =  clientInfo_Email

    if clientInfo_identity_address is None :
        return "Identity address of the client is missing"
    else: 
        clientInfo["identity-address"]  =  clientInfo_identity_address

    if currency is None :
        return "Currency information is missing. value is commonly ETH"
    if price is None :
        return "A service price in ETH is required"
    
    
    invoice_payload = GeneratePayload(clientInfo, currency, price, serviceName)
    payLink, requestId, paymentReference = Send_invoice(invoice_payload)
    
    if payLink is None: 
        return "error in generating invoice, verify your data and try again"
    else: 
        if autoPayment:
            returnString = f"the client can use this payment Reference to perform payment: {paymentReference} to the following address {paymentReceiverAddress}. ID of the invoice is {requestId} and is only for you, you can use it to check the status of payment. If user request or need to pay manually you can provide the following url : {payLink}"
        else:
            returnString = f"URL for payment to send to the client :  {payLink} . ID of the invoice is {requestId} to be used to check the status of payment"
       
        return returnString


def CheckInvoiceStatus(ID, waitingTime):
    """
    CheckInvoiceStatus
    ------------------
    This function checks the current status of an invoice via the Request Network API.
    
    Parameters
    ----------
    ID : str
        The ID of the invoice to check.
    waitingTime : int
        The time to wait (in seconds) before checking the status.
    
    Returns
    -------
    str
        A message describing the current status of the invoice. If the status is still open,
        it advises waiting a few seconds before trying again.
    
    
    """
    # Waiting for the specified time
    time.sleep(waitingTime)

    try:
        # Sending request to get the invoice status
        ServerResponse = requests.get(f"{InvoiceEndpoint}/{ID}", headers = HEADERS)

        # Check if the request was successful
        if ServerResponse.status_code == 200:
            invoice_status_data = ServerResponse.json()
            invoiceStatus = invoice_status_data.get("status", "Unknown")

            # Returning the status message
            return (f"Current status of invoice ID {ID} is: {invoiceStatus}. "
                    "Please wait about 5 seconds before another status check. "
                    "The operation may take some time. If the status is still 'open' after a few tries, "
                    "you should ask for updates. If you need to wait, the internal message should contain "
                    "the waiting time before the next check.")
        else:
            # Return an error message in case of a non-200 response
            return f"Error fetching invoice status. Server responded with status code {ServerResponse.status_code}."

    except requests.RequestException as e:
        # Catch any errors during the request
        return f"An error occurred while checking the invoice status: {e}"

if __name__ == "__main__":
    pass
