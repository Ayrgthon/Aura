import React from 'react';

interface EnergyOrbProps {
  isListening: boolean;
  isSpeaking: boolean;
}

const EnergyOrb: React.FC<EnergyOrbProps> = ({ isListening, isSpeaking }) => {
  return (
    <div className="relative flex items-center justify-center">
      {/* Futuristic blue outer glow ring */}
      <div className="absolute w-80 h-80 rounded-full bg-gradient-radial from-blue-400/15 via-blue-500/8 to-transparent animate-pulse" />
      
      {/* Tech energy rings */}
      <div className="absolute w-60 h-60 rounded-full border border-blue-400/30 animate-spin" style={{ animationDuration: '15s' }} />
      <div className="absolute w-50 h-50 rounded-full border border-cyan-400/25 animate-spin" style={{ animationDuration: '20s', animationDirection: 'reverse' }} />
      <div className="absolute w-40 h-40 rounded-full border border-blue-300/20 animate-spin" style={{ animationDuration: '12s' }} />
      
      {/* Central orb with 3D effect */}
      <div className={`relative w-32 h-32 rounded-full transition-all duration-700 transform-gpu ${
        isListening ? 'scale-125 rotate-12' : isSpeaking ? 'scale-110 rotate-6' : 'scale-100'
      }`}
      style={{
        background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.8), rgba(34, 211, 238, 0.6), rgba(147, 197, 253, 0.4))',
        boxShadow: `
          0 0 50px rgba(59, 130, 246, 0.6),
          0 0 100px rgba(34, 211, 238, 0.4),
          0 0 150px rgba(147, 197, 253, 0.2),
          inset 0 0 30px rgba(255, 255, 255, 0.2)
        `,
        transform: 'perspective(1000px) rotateX(15deg) rotateY(15deg)',
        transformStyle: 'preserve-3d'
      }}>
        {/* Inner glass effect */}
        <div className="absolute inset-2 rounded-full bg-white/15 backdrop-blur-sm" />
        
        {/* Energy core */}
        <div className="absolute inset-6 rounded-full bg-gradient-radial from-cyan-400/60 to-blue-500/30 pulse-slow" />
        
        {/* Holographic scan lines */}
        <div className="absolute inset-0 rounded-full overflow-hidden">
          <div className="absolute w-full h-px bg-gradient-to-r from-transparent via-cyan-400/60 to-transparent animate-pulse" style={{top: '30%', animationDuration: '2s'}} />
          <div className="absolute w-full h-px bg-gradient-to-r from-transparent via-blue-400/40 to-transparent animate-pulse" style={{top: '70%', animationDuration: '3s', animationDelay: '1s'}} />
        </div>
        
        {/* Sound waves when speaking */}
        {isSpeaking && (
          <div className="absolute inset-0 flex items-center justify-center">
            {[...Array(6)].map((_, i) => (
              <div
                key={i}
                className="absolute w-1 bg-white/80 rounded-full wave-animation"
                style={{
                  height: `${25 + i * 10}px`,
                  left: `${40 + i * 10}%`,
                  animationDelay: `${i * 0.15}s`
                }}
              />
            ))}
          </div>
        )}
        
        {/* Enhanced listening pulse effect */}
        {isListening && (
          <div className="absolute inset-0 rounded-full bg-red-400/40 animate-ping" />
        )}
      </div>
      
      {/* Tech floating particles around orb */}
      <div className="absolute inset-0">
        {[...Array(12)].map((_, i) => (
          <div
            key={i}
            className={`absolute rounded-full animate-pulse ${
              i % 3 === 0 ? 'bg-blue-400' : i % 3 === 1 ? 'bg-cyan-400' : 'bg-blue-300'
            }`}
            style={{
              width: `${Math.random() * 2 + 1}px`,
              height: `${Math.random() * 2 + 1}px`,
              left: `${50 + 70 * Math.cos((i * Math.PI * 2) / 12)}%`,
              top: `${50 + 70 * Math.sin((i * Math.PI * 2) / 12)}%`,
              opacity: Math.random() * 0.6 + 0.3,
              animationDelay: `${i * 0.3}s`,
              animationDuration: `${2 + Math.random() * 3}s`
            }}
          />
        ))}
      </div>
    </div>
  );
};

export default EnergyOrb;