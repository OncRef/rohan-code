"use client";
import React from 'react';
import { useState, useEffect } from 'react';
import axios from 'axios';

const Page = () => {
    const [playerName, setPlayerName] = useState('DEFAULT');
    const [data, setData] = useState([]);
    const [flagCount, setFlagCount] = useState(false)

    async function getData(selectedPlayer) {
        const response = await fetch(`/api/ncts/stuff?player=${selectedPlayer}`, {
            method: "GET"
        });
        const res = await response.json();
        setData(res.data);
        setFlagCount(res.flaggedCount);
    }

    // async function handleRedo(drug) {
    //     try {
    //       const response = await axios.post("/api/redo", drug);
    //       if (response.status === 200) {  
    //         alert("Data has been updated");
    //         getData(playerName);
    //       } else {
    //         alert("Failed to update data");
    //       }
    //     } catch (error) {
    //       console.error("Error updating data:", error);
    //       alert("An error occurred while updating data");
    //     }
    // }

    useEffect(() => {
        if (playerName !== "DEFAULT") {
            getData(playerName);
        }
    }, [playerName]);

    const formatTrials = (trials) => {
        let s = "";
        if (typeof trials === 'object' && Array.isArray(trials) && trials !== null) {
            for (let trial of trials) {
                s += `${trial.sub_cancer || `""`} --> ${trial.ncts || `""`}\n`
            }
        }
        return s.trim()
    }

    return (
        <div className="min-h-screen bg-black text-white p-8">
            <div className="max-w-full mx-auto">
                <h1 className="text-4xl font-bold mb-2 text-center text-green-400">NCT Game Stats : {data.length}</h1>
                <h3 className="text-3xl font-bold mb-8 text-center text-yellow-400">Flagged (Global) : {flagCount}</h3>
                
                <div className='flex items-center justify-center mb-12'>
                    <label htmlFor="player" className="mr-4 text-lg text-green-200">Select Player:</label>
                    <select 
                        id="player" 
                        className="px-4 py-2 bg-gray-900 text-white border border-r-8 border-transparent outline outline-green-500 transition duration-300 ease-in-out hover:bg-gray-800" 
                        value={playerName} 
                        onChange={e => setPlayerName(e.target.value)}>
                        <option value='DEFAULT'>Choose a player</option>
                        <option value='tom'>Tom</option>
                        <option value='raena'>Raena</option>
                        <option value='yash'>Yash</option>
                        <option value='sneha'>Sneha</option>
                        <option value='daksh'>Daksh</option>
                    </select>
                </div>

                {data && data.length > 0 ? (
                    // <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                     <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {data.map((drug, index) => (
                            <div key={index} className="bg-gray-900 rounded-lg shadow-lg overflow-hidden transition duration-300 ease-in-out hover:shadow-green-500/20 hover:shadow-2xl border border-gray-800">
                                <div className="bg-gray-800 px-6 py-4">
                                    {/* <div className='flex items-center justify-between'>
                                        <h2 className="text-2xl font-semibold text-green-400">{drug.generic_name}</h2>
                                        <button 
                                            className='text-sm bg-green-700 hover:bg-green-600 text-white rounded-lg p-2 transition duration-300 ease-in-out' 
                                            onClick={() => handleRedo(drug)}>
                                            ReDo
                                        </button>
                                    </div> */}
                                    <p className="text-sm text-gray-400">ID: {drug._id}</p>
                                </div>
                                <div className="px-6">
                                    {/* <h3 className="text-xl font-semibold mb-4 text-green-300">NCT</h3> */}
                                    {drug.indications.map((indication, ind_index)=> (
                                        <div className="my-5" key={ind_index}>
                                            <p className="text-sm m-0.5 text-white">{indication.extracted_cancer}</p>
                                            <p className='text-sm m-0.5 text-gray-500'>{indication.description}</p>
                                            <p className='text-sm m-0.5 text-gray-300 whitespace-pre-wrap'>{formatTrials(indication.trials)}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <p className="text-center text-gray-400 text-lg">Select a player to view their data.</p>
                )}
            </div>
        </div>
    );
}

export default Page;