import { NextResponse } from "next/server";
import clientPromise from "@/lib/mongodb";

export async function GET() {
    try {
        const client = await clientPromise;
        const db = client.db("OncRef_Game");
        const filters = {
            approved: false,
            locked: false,
        };
        const pipeline = [
            { $match: filters },
            { $sample: { size: 1 } },
        ];
        const result = await db.collection("pressreleases").aggregate(pipeline).toArray();
        if (result.length === 0) {
            return NextResponse.json(
                { message: "No press release found." },
                { status: 400 }
            );
        }
        const drug = result[0];
        return NextResponse.json(drug);
    } catch (error) {
        console.error("Error fetching data:", error);
        return NextResponse.json(
            { message: "Internal server error." },
            { status: 400 }
        );
    }
}
