import React, { useEffect, useState } from 'react';
import Draggable from 'react-draggable';

interface DraggablePanelProps {
  id: string;
  children: React.ReactNode;
  defaultPosition?: { x: number; y: number };
}

const getSavedPosition = (id: string, def: { x: number; y: number }) => {
  if (typeof window === 'undefined') return def;
  const saved = localStorage.getItem(`panel-pos-${id}`);
  if (saved) {
    try {
      return JSON.parse(saved);
    } catch {
      return def;
    }
  }
  return def;
};

const DraggablePanel: React.FC<DraggablePanelProps> = ({ id, children, defaultPosition = { x: 0, y: 0 } }) => {
  const [position, setPosition] = useState(() => getSavedPosition(id, defaultPosition));

  useEffect(() => {
    localStorage.setItem(`panel-pos-${id}`, JSON.stringify(position));
  }, [id, position]);

  return (
    <Draggable
      handle=".drag-handle"
      position={position}
      onStop={(_, data) => setPosition({ x: data.x, y: data.y })}
    >
      <div style={{ position: 'absolute', zIndex: 30 }}>
        {children}
      </div>
    </Draggable>
  );
};

export default DraggablePanel; 