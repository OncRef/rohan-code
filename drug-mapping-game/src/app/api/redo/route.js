import { NextResponse } from "next/server";
import clientPromise from "@/lib/mongodb";

export async function POST(req) {
  try {
    const data = await req.json();
    const setid = data._id;
    const processedindications = data.indications;
    const client = await clientPromise;
    const db = client.db("OncRef_Game");
    const updateResult = await db.collection("original_drug_data").findOneAndUpdate(
      { "_id": setid },
      {
        $set: {
          processedind: processedindications,
          locked: "N",
          approved: "N"
        }
      }
    );
    if (updateResult) {
      const deleteResult = await db.collection("new_drug_data").findOneAndDelete(
        { "_id": setid }
      );
      if(deleteResult) return new NextResponse({success:true}, { status: 200 });
    }
    return NextResponse.json({ success: false, message: "Failed to update or delete data" }, { status: 500 });
  } catch (error) {
    console.log(error);
    return NextResponse.json({ error: error.message }, { status: 400 });
  }
}
