import React, { useEffect, useRef, useState } from "react";

const AutoResizeTextarea = ({ content, onChange, disabled = false, placeholder = "" }) => {
  const textareaRef = useRef(null);
  const [value, setValue] = useState(content);

  useEffect(() => {
    setValue(content);
  }, [content]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"; // Reset height
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`; // Adjust height
    }
  }, [value]); // Re-run if content changes

  const handleChange = (e) => {
    const newValue = e.target.value;
    setValue(newValue);
    if (onChange) {
      onChange(newValue);
    }
  };

  return (
    <textarea
      ref={textareaRef}
      className="w-full border rounded p-2 resize-none overflow-hidden text-black"
      disabled={disabled}
      value={value}
      onChange={handleChange}
      placeholder={placeholder}
    />
  );
};

export default AutoResizeTextarea;