import type { PoseFrame } from "./poseTypes";

export class PoseHistory {
  private buffer: PoseFrame[] = [];
  private maxlen: number;

  constructor(maxlen = 90) {
    this.maxlen = maxlen;
  }

  append(pose: PoseFrame): void {
    this.buffer.push(pose);
    if (this.buffer.length > this.maxlen) {
      this.buffer.shift();
    }
  }

  latest(): PoseFrame | null {
    return this.buffer.length ? this.buffer[this.buffer.length - 1] : null;
  }

  latestValid(): PoseFrame | null {
    for (let i = this.buffer.length - 1; i >= 0; i -= 1) {
      if (this.buffer[i].valid) {
        return this.buffer[i];
      }
    }
    return null;
  }

  recent(count: number): PoseFrame[] {
    if (count <= 0) {
      return [];
    }
    return this.buffer.slice(-count);
  }

  timeWindow(seconds: number): PoseFrame[] {
    if (!this.buffer.length) {
      return [];
    }
    const endTime = this.buffer[this.buffer.length - 1].timestamp;
    return this.buffer.filter((pose) => endTime - pose.timestamp <= seconds);
  }
}

