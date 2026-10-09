import { Component, type ReactNode } from 'react'

/** Renders `fallback` if anything below throws (e.g. a model that fails to load), so one asset can't take the page down. */
export class Fallback extends Component<{ fallback: ReactNode; children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() {
    return { failed: true }
  }
  render() {
    return this.state.failed ? this.props.fallback : this.props.children
  }
}
