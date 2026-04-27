import { NextResponse } from "next/server";
import clientPromise from "@/lib/mongodb";

export async function GET(req) {
    try {
        const url = new URL(req.url);
        const player = url.searchParams.get("player");
        if (!player) {
            return NextResponse.json({ success: false, message: "Player parameter is required" }, { status: 400 });
        }
        const client = await clientPromise;
        const db = client.db("OncRef_Game");
        const data = await db.collection("all_drugs").find({ "nct_game_approved_by": player }).toArray();
        const flaggedCount = await db.collection("all_drugs").countDocuments({ "nct_game_flag": 'Y' })
        return NextResponse.json({ success: true, data: data, flaggedCount: flaggedCount });
    } catch (error) {
        console.error("Error fetching data:", error);
        return NextResponse.json({ success: false, message: "Something went wrong!" }, { status: 500 });
    }
};
