import { useEffect, useState } from 'react';
import './SpeechBubble.css';

interface SpeechBubbleProps {
  message: string;
  isVisible: boolean;
  position?: 'left' | 'right' | 'center';
}

export function SpeechBubble({ message, isVisible, position = 'center' }: SpeechBubbleProps) {
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (isVisible) {
      setShow(true);
    } else {
      const timer = setTimeout(() => setShow(false), 300);
      return () => clearTimeout(timer);
    }
  }, [isVisible]);

  if (!show && !isVisible) return null;

  return (
    <div className={`speech-bubble ${position} ${isVisible ? 'visible' : 'hidden'}`}>
      <div className="speech-bubble-content">
        {message}
      </div>
      <div className="speech-bubble-tail" />
    </div>
  );
}
