/** Resolves when the lazy story chunk has mounted; the loader waits for it before it hands over (#207). */
export let storyMounted = () => {}
export const storyReady = new Promise<void>((r) => (storyMounted = r))
