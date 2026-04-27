"use client";
import React, { useState, useEffect } from "react";
import axios from "axios";
import { DndProvider, useDrag, useDrop } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";

const Page = () => {
  const [drug, setDrug] = useState(null);
  const [matches, setMatches] = useState([]);

  async function lockid(id) {
    const response = await axios.post("/api/gamepress/locker", {
      _id: id,
    });
    if (response.status === 200) console.log("locked", id);
  }

  async function fetchData() {
    const response = await axios.get("/api/gamepress/getter");
    if (response.status === 400) {
      fetchData();
    }
    const id = response.data._id;
    lockid(id);
    setDrug(response.data);
  }

  useEffect(() => {
    if (confirm("Do you want to start playing? Are you ready?")) {
      fetchData();
    } else {
      window.close();
    }
  }, []);

  const saveData = () => {
    const dataToSave = drug.indications.map((indication) => {
      const associatedPressReleases = matches.filter(
        (match) => match.indication === indication.extracted_cancer
      );
      return {
        indication: indication.extracted_cancer,
        press_releases: associatedPressReleases.length
          ? associatedPressReleases.map((match) => match.press_release)
          : [],
      };
    });

    console.log("Saving data:", dataToSave);
  };

  if (!drug) {
    return (
      <div className="bg-black min-h-screen text-white font-sans py-2">
        <h1 className="text-center font-bold text-lg">Press Release Game</h1>
        <h1>Fetching............ or contact tech</h1>
      </div>
    );
  }

  return (
    <DndProvider backend={HTML5Backend}>
      <div className="bg-black min-h-screen text-white font-sans py-4">
        <h1 className="text-center font-bold text-3xl">Press Release Game</h1>
        <div className="mt-7 text-white justify-evenly flex">
          <button
            className=""
            onClick={saveData}>
            Save
          </button>
          <button onClick={() => window.close()}>Exit</button>
        </div>
        <h1 className="text-center font-bold text-xl">{drug.generic_name}</h1>
        <div className="flex justify-between mt-5 gap-x-2">
          <Indications drug={drug} matches={matches} setMatches={setMatches} />
          <PressReleases drug={drug} />
        </div>
      </div>
    </DndProvider>
  );
};

const Indications = ({ drug, matches, setMatches }) => {
  return (
    <div className="p-8 w-full md:w-1/2 bg-gray-900 rounded-lg shadow-lg">
      <h1 className="text-3xl font-bold mb-6 text-gray-100 border-b border-gray-700 pb-2">Indications</h1>
      {drug.indications.map((indication) => (
        <IndicationBox
          key={indication.extracted_cancer}
          indication={indication.extracted_cancer}
          desc={indication.description}
          matches={matches}
          setMatches={setMatches}
        />
      ))}
    </div>
  );
};

const IndicationBox = ({ indication, matches, setMatches, desc }) => {
  const [, drop] = useDrop({
    accept: "PRESS_RELEASE",
    drop: (item) => {
      setMatches((prev) => [...prev, { indication, press_release: item }]);
    },
  });

  const removeMatch = (matchToRemove) => {
    setMatches((prev) =>
      prev.filter((match) => match !== matchToRemove)
    );
  };

  return (
    <div
      ref={drop}
      className="border border-gray-500 p-4 mt-3 bg-gray-800 rounded" key={indication}>
      <h2>{indication}</h2>
      <h1>{desc}</h1>
      <div className="mt-2">
        {matches
          .filter((match) => match.indication === indication)
          .map((match, index) => (
            <div
              key={index}
              className="bg-gray-700 p-2 mt-2 rounded flex justify-between items-center">
              <span>{match.press_release.title}</span>
              <button
                onClick={() => removeMatch(match)}
                className="text-red-500 hover:text-red-700">
                X
              </button>
            </div>
          ))}
      </div>
    </div>
  );
};

const PressReleases = ({ drug }) => {
  return (
    <div className="p-8 w-full md:w-1/2 bg-gray-900 rounded-lg shadow-lg" key={drug.generic_name}>
      <h1 className="text-3xl font-bold mb-6 text-gray-100 border-b border-gray-700 pb-2">Press Releases {drug.generic_name}</h1>
      {drug.press_data.map((press) => (
        <PressRelease key={press.link} press={press} />
      ))}
    </div>
  );
};

const PressRelease = ({ press }) => {
  const [{ isDragging }, drag] = useDrag({
    type: "PRESS_RELEASE",
    item: press,
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
  });

  return (
    <div ref={drag} className={`border border-gray-500 p-4 mt-3 cursor-pointer rounded bg-gray-800 ${isDragging ? "opacity-50" : ""}`} key={press.title}>
        <h1 className="font-bold mb-2">{press.title}</h1>
        <div className="h-52 overflow-y-scroll">
            <p className="text-sm">{press.blob}</p>
        </div>
    </div>
  );
};

export default Page;
