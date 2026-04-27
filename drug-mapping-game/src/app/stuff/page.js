"use client";
import React from 'react';
import { useState, useEffect } from 'react';
import axios from 'axios';

const Page = () => {
    const [playerName, setPlayerName] = useState('DEFAULT');
    const [data, setData] = useState([]);

    async function getData(selectedPlayer) {
        const response = await fetch(`/api/getdata?player=${selectedPlayer}`, {
            method: "GET"
        });
        const yo = await response.json();
        setData(yo.data);
    }

    async function handleRedo(drug) {
        try {
          const response = await axios.post("/api/redo", drug);
          if (response.status === 200) {  
            alert("Data has been updated");
            getData(playerName);
          } else {
            alert("Failed to update data");
          }
        } catch (error) {
          console.error("Error updating data:", error);
          alert("An error occurred while updating data");
        }
    }

    useEffect(() => {
        if (playerName !== "DEFAULT") {
            getData(playerName);
        }
    }, [playerName]);

    return (
        <div className="min-h-screen bg-black text-white p-8">
            <div className="max-w-4xl mx-auto">
                <h1 className="text-4xl font-bold mb-8 text-center text-green-400">Stats & Data : {data.length}</h1>
                
                <div className='flex items-center justify-center mb-12'>
                    <label htmlFor="player" className="mr-4 text-lg text-green-200">Select Player:</label>
                    <select 
                        id="player" 
                        className="px-4 py-2 bg-gray-900 text-white rounded-full border border-green-500 focus:outline-none focus:ring-2 focus:ring-green-600 focus:border-transparent transition duration-300 ease-in-out hover:bg-gray-800" 
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
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                        {data.map((drug, index) => (
                            <div key={index} className="bg-gray-900 rounded-lg shadow-lg overflow-hidden transition duration-300 ease-in-out hover:shadow-green-500/20 hover:shadow-2xl border border-gray-800">
                                <div className="bg-gray-800 px-6 py-4">
                                    <div className='flex items-center justify-between'>
                                        <h2 className="text-2xl font-semibold text-green-400">{drug.generic_name}</h2>
                                        <button 
                                            className='text-sm bg-green-700 hover:bg-green-600 text-white rounded-lg p-2 transition duration-300 ease-in-out' 
                                            onClick={() => handleRedo(drug)}>
                                            ReDo
                                        </button>
                                    </div>
                                    <p className="text-sm text-gray-400">ID: {drug._id}</p>
                                </div>
                                <div className="p-6">
                                    <h3 className="text-xl font-semibold mb-4 text-green-300">Indications</h3>
                                    {drug.indications.map((indication)=> (
                                        <div key={indication.extracted_cancer}>
                                            {console.log(indication)}
                                            <p className="text-sm text-gray-400">{indication.extracted_cancer}</p>
                                            <p className='text-sm text-gray-500'>{indication.description}</p>
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