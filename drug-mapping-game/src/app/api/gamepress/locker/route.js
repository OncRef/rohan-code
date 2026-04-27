import { NextResponse } from "next/server";
import clientPromise from "@/lib/mongodb";
import { ObjectId } from "mongodb";

export async function POST(req) {
  try {
    let data = await req.json();
    let _id = data._id;
    console.log(_id);
    const client = await clientPromise;
    const db = client.db("OncRef_Game");
    const result = await db.collection("pressreleases").updateOne(
      { _id: new ObjectId(_id) }, 
      { $set: { locked: true } } 
    );
    return NextResponse.json(
      { message: "Document updated successfully." },
      { status: 200 }
    );
  } catch (e) {
    console.error("Error:", e);
    return NextResponse.json({ error: "Internal server error." }, { status: 500 });
  }
}
