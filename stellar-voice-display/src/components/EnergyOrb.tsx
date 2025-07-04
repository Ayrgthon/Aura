import React from 'react';

interface EnergyOrbProps {
  isListening: boolean;
  isSpeaking: boolean;
}

const EnergyOrb: React.FC<EnergyOrbProps> = ({ isListening, isSpeaking }) => {
  return (
    <div className="relative flex items-center justify-center">
      {/* Outer glow ring */}
      <div className="absolute w-80 h-80 rounded-full bg-gradient-radial from-primary/20 via-primary/5 to-transparent animate-pulse" />
      
      {/* Energy rings */}
      <div className="absolute w-64 h-64 rounded-full border border-primary/30 animate-spin" style={{ animationDuration: '10s' }} />
      <div className="absolute w-52 h-52 rounded-full border border-accent/20 animate-spin" style={{ animationDuration: '15s', animationDirection: 'reverse' }} />
      
      {/* Central orb */}
      <div className={`relative w-32 h-32 rounded-full transition-all duration-500 orb-glow ${
        isListening ? 'scale-125' : isSpeaking ? 'scale-110' : 'scale-100'
      }`}>
        <div className="absolute inset-0 rounded-full bg-gradient-to-r from-primary via-accent to-neon-magenta animate-spin" style={{ animationDuration: '3s' }} />
        <div className="absolute inset-1 rounded-full bg-background/20 backdrop-blur-sm" />
        
        {/* Inner energy core */}
        <div className="absolute inset-4 rounded-full bg-gradient-radial from-energy-glow to-primary/50 pulse-slow" />
        
        {/* Sound waves when speaking */}
        {isSpeaking && (
          <div className="absolute inset-0 flex items-center justify-center">
            {[...Array(5)].map((_, i) => (
              <div
                key={i}
                className="absolute w-1 bg-primary/80 rounded-full wave-animation"
                style={{
                  height: `${20 + i * 8}px`,
                  left: `${45 + i * 8}%`,
                  animationDelay: `${i * 0.1}s`
                }}
              />
            ))}
          </div>
        )}
        
        {/* Listening pulse effect */}
        {isListening && (
          <div className="absolute inset-0 rounded-full bg-destructive/30 animate-ping" />
        )}
      </div>
      
      {/* Floating particles around orb */}
      {(isListening || isSpeaking) && (
        <div className="absolute inset-0">
          {[...Array(8)].map((_, i) => (
            <div
              key={i}
              className="absolute w-2 h-2 bg-primary rounded-full opacity-60 animate-pulse"
              style={{
                left: `${50 + 40 * Math.cos((i * Math.PI * 2) / 8)}%`,
                top: `${50 + 40 * Math.sin((i * Math.PI * 2) / 8)}%`,
                animationDelay: `${i * 0.2}s`,
                animationDuration: '1.5s'
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default EnergyOrb;