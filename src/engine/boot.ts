/** Resolves when the page's own content has mounted: the lazy story chunk on /story, the sections on the homepage. */
export let storyMounted = () => {}
export const storyReady = new Promise<void>((r) => (storyMounted = r))
