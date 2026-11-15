// Count advancing audio only; a seek, pause, or suspended timer adds no time.
export class ListenedTime {
  constructor() {
    this.seconds = 0
    this.position = null
    this.clock = null
  }
  sample(position, clock, playing) {
    if (this.position !== null && this.clock !== null && playing) {
      const movement = position - this.position
      const elapsed = (clock - this.clock) / 1000
      if (
        elapsed > 0 &&
        elapsed <= 3 &&
        movement > 0 &&
        movement <= elapsed * 1.25 + 0.2
      ) {
        this.seconds += Math.min(movement, elapsed)
      }
    }
    this.position = position
    this.clock = clock
    return this.seconds
  }
}
