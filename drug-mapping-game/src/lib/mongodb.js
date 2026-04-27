import { MongoClient } from 'mongodb'

const uri = process.env.MONGODB_URI || "mongodb+srv://***REDACTED***@oncref.se0af.mongodb.net/?retryWrites=true&w=majority&appName=OncRef"

let client
let clientPromise

if (!uri) {
  throw new Error('Please add your Mongo URI to .env.local')
}

if (process.env.NODE_ENV === 'development') {
  if (!global._mongoClientPromise) {
    client = new MongoClient(uri)
    global._mongoClientPromise = client.connect()
  }
  clientPromise = global._mongoClientPromise
} else {
  client = new MongoClient(uri)
  clientPromise = client.connect()
}

// console.log(uri)

export default clientPromise