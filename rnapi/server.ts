import express from 'express';
import { Request, Response } from 'express';
import dotenv from 'dotenv';
import { RequestNetwork, Types, PaymentReferenceCalculator, Utils } from '@requestnetwork/request-client.js';
import { EthereumPrivateKeySignatureProvider } from '@requestnetwork/epk-signature';
import { getTheGraphClient } from "@requestnetwork/payment-detection";

dotenv.config();

const app = express();
const port = process.env.PORT || 3000;

app.use(express.json());

// Environment variables
const API_KEY = process.env.RequestNetwork_API_KEY;


// Middleware for API key authentication
const authenticateApiKey = (req: Request, res: Response, next: Function) => {
  const apiKey = req.header('Authorization');
  if (apiKey !== API_KEY) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  next();
};

// ################ Initialisation ######################################
// payee information
const payeeSignatureInfo = {
  method: Types.Signature.METHOD.ECDSA,
  privateKey: '0xc87509a1c067bbde78beb793e6fa76530b6382a4c0241e5e4a9ec0a0f44dc0d3',
};

// Signature providers
const signatureProvider = new EthereumPrivateKeySignatureProvider();
const payee = signatureProvider.addSignatureParameters(payeeSignatureInfo);

const requestNetwork = new RequestNetwork({
  signatureProvider,
  nodeConnectionConfig: { 
    baseURL: 'https://sepolia.gateway.request.network/' 
  },
  paymentOptions: {
    getSubgraphClient: (chain: string) => {
      // Ternary because cannot dynamically access environment variables in the browser
      const paymentsSubgraphUrl =
        chain === "sepolia"
          ? process.env.NEXT_PUBLIC_PAYMENTS_SUBGRAPH_URL_SEPOLIA || "https://subgraph.satsuma-prod.com/e2e4905ab7c8/request-network--434873/request-payments-sepolia/api"
          : undefined;
      if (!paymentsSubgraphUrl) {
        throw new Error(`Cannot get subgraph client for unknown chain: ${chain}`);
      }
      return getTheGraphClient(chain, paymentsSubgraphUrl);
    },
  },
});
// ######################################################



// Routes

// POST /invoices
app.post('/invoices', authenticateApiKey, async (req: Request, res: Response) => {
  if(!req.body.currency) {
    throw Error('currency not found');
  }
  if(req.body.currency !== 'ETH-sepolia') {
    return res.status(400).json({ error: 'currency must be ETH-sepolia' });
  }
  
  if(!req.body.expectedAmount) {
    return res.status(400).json({ error: 'expectedAmount not found' });
  }
  if(!req.body.payerAddress) {
    return res.status(400).json({ error: 'payerAddress not found' });
  }
  if(!req.body.paymentAddress) {
    return res.status(400).json({ error: 'paymentAddress not found' });
  }
  if(!req.body.contentdata) {
    return res.status(400).json({ error: 'contentdata not found' });
    
  }

  const requestInfo: Types.IRequestInfo = {
    currency: req.body.currency,
    expectedAmount: req.body.expectedAmount,
    payee,
    payer: {
      value: req.body.payerAddress,
      type: Types.Identity.TYPE.ETHEREUM_ADDRESS
    },
  };
  
  const paymentNetwork: Types.Payment.PaymentNetworkCreateParameters = {
    id: Types.Extension.PAYMENT_NETWORK_ID.ETH_FEE_PROXY_CONTRACT,
    parameters: {
      paymentAddress: req.body.paymentAddress,
      feeAddress: '0x0000000000000000000000000000000000000000',
      feeAmount: '0'
    },
  };

  const createParams = {
    paymentNetwork,
    requestInfo,
    signer: payee,
    contentdata: req.body.contentdata
  };

  const request = await requestNetwork.createRequest(createParams);

  // Wait for confirmation
  const requestData = await request.waitForConfirmation();

  const paymentReference = PaymentReferenceCalculator.calculate(
    request.requestId,
    requestData.extensions[Types.Extension.ID.ETH_FEE_PROXY_CONTRACT].values.salt,
    req.body.paymentAddress
  );

  res.status(201).json({ id: request.requestId, paymentReference });
});


// GET /invoices/:id
app.get('/invoices/:id', authenticateApiKey, async (req: Request, res: Response) => {
  const { id } = req.params;

  const request = await requestNetwork.fromRequestId(id);
  const requestData = await request.refreshBalance();
  const expectedAmount = request.getData().expectedAmount;

  if(!requestData || !requestData.balance || BigInt(requestData?.balance) < BigInt(expectedAmount)) {
    res.status(200).json({ status: 'open', requestData });
  } else {
    res.status(200).json({ status: 'paid', requestData });
  }
});


// Start the server
app.listen(port, () => {
  console.log(`Server running on port ${port}`);
});
