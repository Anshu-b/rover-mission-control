import { Radio, Satellite } from "lucide-react";

const MissionHeader = () => {
  return (
    <header className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-primary/10 border border-primary/30 flex items-center justify-center glow-primary">
          <Satellite className="w-5 h-5 text-primary" />
        </div>
        <div>
          <h1 className="font-display text-lg sm:text-xl font-bold tracking-wider text-foreground text-glow-primary">
            MISSION CONTROL
          </h1>
          <p className="font-mono text-[10px] text-muted-foreground tracking-widest">
            AUTONOMOUS ROVER · EARTH CONTROL DASHBOARD
          </p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-success/10 border border-success/30">
          <Radio className="w-3 h-3 text-success animate-pulse-glow" />
          <span className="font-mono text-[10px] text-success tracking-wider">LINK ACTIVE</span>
        </div>
        <div className="font-mono text-[10px] text-muted-foreground">
          <span className="text-foreground/60">LAT</span> -14.4673°{" "}
          <span className="text-foreground/60 ml-2">LON</span> 175.4726°
        </div>
      </div>
    </header>
  );
};

export default MissionHeader;
