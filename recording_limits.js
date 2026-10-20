// Decimal GB throughout. Frame sampling is independent of native pen input.
export const LIMITS={width:1280,height:720,fps:30,videoBitrate:4500000,audioBitrate:128000,maxSeconds:10800,warnSeconds:9000,maxBytes:5000000000,warnBytes:4000000000,finalReserve:8*1024*1024};
export function recordingLimits(seconds,bytes,limits=LIMITS){return {timeWarning:seconds>=limits.warnSeconds,sizeWarning:bytes>=limits.warnBytes,stop:seconds>=limits.maxSeconds?'time':bytes>=limits.maxBytes-limits.finalReserve?'size':null};}
