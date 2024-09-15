from web3 import Web3
from web3.utils import log_topic_to_bytes
import os


# Initialize Web3 connection with Infura URL for Sepolia network
infura_url = os.getenv("infura_url_key")
# Get metamask account private key
private_key_metamask =  os.getenv("PRIVATEKEYMETAMASK")
# Get metamask account AI wallet address
AIWallet = os.getenv("WalletPaymentMetamask")

# Proxy smart contracts for ETH see https://docs.request.network/get-started/protocol-overview/how-payment-networks-work 
contract_address = "0xe11BF2fDA23bF0A98365e1A4c04A87C9339e8687"  
# Fee address for the transaction
fee_address = "0x35d0e078755Cd84D3E0656cAaB417Dee1d7939c7"

# Initialize Web3 connection
web3Connex = Web3(Web3.HTTPProvider(infura_url))
#ABI of the smart contract used for interaction
ABI_json = """[{"anonymous":false,"inputs":[{"indexed":false,"internalType":"address","name":"to","type":"address"},{"indexed":false,"internalType":"uint256","name":"amount","type":"uint256"},{"indexed":true,"internalType":"bytes","name":"paymentReference","type":"bytes"},{"indexed":false,"internalType":"uint256","name":"feeAmount","type":"uint256"},{"indexed":false,"internalType":"address","name":"feeAddress","type":"address"}],"name":"TransferWithReferenceAndFee","type":"event"},{"inputs":[{"internalType":"address payable","name":"_to","type":"address"},{"internalType":"uint256","name":"_amount","type":"uint256"},{"internalType":"bytes","name":"_paymentReference","type":"bytes"},{"internalType":"uint256","name":"_feeAmount","type":"uint256"},{"internalType":"address payable","name":"_feeAddress","type":"address"}],"name":"transferExactEthWithReferenceAndFee","outputs":[],"stateMutability":"payable","type":"function"},{"inputs":[{"internalType":"address payable","name":"_to","type":"address"},{"internalType":"bytes","name":"_paymentReference","type":"bytes"},{"internalType":"uint256","name":"_feeAmount","type":"uint256"},{"internalType":"address payable","name":"_feeAddress","type":"address"}],"name":"transferWithReferenceAndFee","outputs":[],"stateMutability":"payable","type":"function"},{"stateMutability":"payable","type":"receive"}]"""

def PerformPayment(recipient_address, amount_to_pay, paymentRefence):
    """
    PerformPayment
    --------------
    Executes a payment through a smart contract on the Sepolia testnet using Web3.py.
    
    Parameters
    ----------
    recipient_address : str
        The Ethereum address of the payment recipient.
    amount_to_pay : float
        The amount to be paid in ETH.
    paymentRefence : str
        A reference for the payment, used to track the transaction. Must be a string that will be converted to bytes.

    Returns
    -------
    str
        A message indicating the result of the transaction: either "transaction is confirmed" or an error message.
    
    Notes
    -----
    - The function interacts with a smart contract that uses a method `transferWithReferenceAndFee`.
    - The fee for this transaction is set to 0.
    - The transaction is signed locally with the provided private key and sent to the blockchain.
    - The function waits for the transaction receipt to confirm whether the transaction succeeded or failed.
   
    """  
    if recipient_address is None : 
        return "Error , a valid recipient_address should be provided."
    # Initialize the smart contract with address and ABI
    contract_instance = web3Connex.eth.contract(address=contract_address, abi=ABI_json)

    # Convert the ETH amount to Wei (smallest unit of ETH)
    eth_value = amount_to_pay
    fee_amount = 0 # No fee for this transaction
    amount_to_send = web3Connex.to_wei(eth_value, 'ether')
   
    paymentReference_bytes =log_topic_to_bytes(paymentRefence) # Convert payment reference to bytes

    # Build the transaction
    txn = contract_instance.functions.transferWithReferenceAndFee(
        recipient_address,  
        paymentReference_bytes,  # payment reference in bytes
        fee_amount,  # Fee amount (0 in this case)
        fee_address # Fee address (set but not used since fee = 0)
    ).build_transaction({
            'from': AIWallet,
            'value': amount_to_send,  
            'nonce': web3Connex.eth.get_transaction_count(AIWallet),
            'chainId': 11155111,  # Sepolia testnet chain ID
        })
    # Sign the transaction with the private key
    signed_txn = web3Connex.eth.account.sign_transaction(txn, private_key_metamask)

    # Send the signed transaction
    txn_hash = web3Connex.eth.send_raw_transaction(signed_txn.raw_transaction)

    # Wait for the transaction receipt (confirmation)
    
    txn_receipt = web3Connex.eth.wait_for_transaction_receipt(txn_hash)
    if  txn_receipt.status == 1: 
        return "transaction is confirmed"
    else: 
        return "error during the transaction execution or timeout in waiting for completion"
