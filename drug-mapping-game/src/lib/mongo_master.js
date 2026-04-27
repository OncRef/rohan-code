import { MongoClient } from 'mongodb'

const uri = process.env.MONGODB_URI

let client
let clientMasterPromise

if (!uri) {
  throw new Error('Please add your Mongo URI to .env.local')
}

if (process.env.NODE_ENV === 'development') {
  if (!global._mongoclientMasterPromise) {
    client = new MongoClient(uri)
    global._mongoclientMasterPromise = client.connect()
  }
  clientMasterPromise = global._mongoclientMasterPromise
} else {
  client = new MongoClient(uri)
  clientMasterPromise = client.connect()
}

export default clientMasterPromise