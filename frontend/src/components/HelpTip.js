import React, { useState } from 'react';

function HelpTip({ text }) {
  const [visible, setVisible] = useState(false);

  return (
    <span className="help-tip-wrapper">
      <button
        className="help-tip-btn"
        onMouseEnter={() => setVisible(true)}
        onMouseLeave={() => setVisible(false)}
        onClick={(e) => { e.preventDefault(); setVisible(!visible); }}
        type="button"
        aria-label="Help"
      >
        ?
      </button>
      {visible && (
        <span className="help-tip-bubble">{text}</span>
      )}
    </span>
  );
}

export default HelpTip;
