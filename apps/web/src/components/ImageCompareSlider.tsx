import { useState } from "react";
import { afterImageClipPath } from "../lib/imageCompare";

type Props = {
  beforeUrl: string;
  afterUrl: string;
  beforeLabel: string;
  afterLabel: string;
};

export function ImageCompareSlider({ beforeUrl, afterUrl, beforeLabel, afterLabel }: Props) {
  const [position, setPosition] = useState(50);
  const [failed, setFailed] = useState(false);

  if (failed) {
    return (
      <div className="compare-fallback">
        <div>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={afterUrl} alt={afterLabel} />
          <span>{afterLabel}</span>
        </div>
        <div>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={beforeUrl} alt={beforeLabel} />
          <span>{beforeLabel}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="compare-slider">
      <div className="compare-frame">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img className="compare-image" src={beforeUrl} alt={beforeLabel} onError={() => setFailed(true)} />
        <div className="compare-after" style={{ clipPath: afterImageClipPath(position) }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img className="compare-image" src={afterUrl} alt={afterLabel} onError={() => setFailed(true)} />
        </div>
        <div className="compare-handle" style={{ left: `${position}%` }} />
        <span className="compare-label compare-label-before">{afterLabel}</span>
        <span className="compare-label compare-label-after">{beforeLabel}</span>
      </div>
      <input
        aria-label="调整原图和结果图对比位置"
        className="compare-range"
        max="100"
        min="0"
        type="range"
        value={position}
        onChange={(event) => setPosition(Number(event.target.value))}
      />
    </div>
  );
}
