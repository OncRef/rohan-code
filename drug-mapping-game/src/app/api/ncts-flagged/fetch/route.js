import { NextResponse } from 'next/server'
import clientPromise from '@/lib/mongodb'

export async function GET() {
    try {
        const client = await clientPromise;
        const db = client.db('OncRef_Game');

        // const drug = await db.collection("original_drug_data").findOne({
        //     'approved': 'N',
        //     'locked': 'N'
        // });

        const filters1 = {
            reviewed: 'Y',
            nct_game_approved: 'N',
            nct_game_flag: 'Y',
            nct_game_locked: 'N',
            ncts: { $ne: "" }
        }

        const filters2 = {
            reviewed: 'Y',
            nct_game_approved: 'N',
            nct_game_flag: 'Y',
            nct_game_locked: 'N'
        }

        const sortCriteria = {
            generic_name: 1,
            _id: 1
        }

        const drug = await db.collection("all_drugs").findOne(filters1, {sort: sortCriteria})
        // const drug = await db.collection("all_drugs").findOne(filters1)
        
        // console.log(drug)

        return NextResponse.json(drug);
    } catch (error) {
        console.error("Failed to fetch drug:", error);
        return NextResponse.json({ success: false, error: error.message }, { status: 500 })
    }
}