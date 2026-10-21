declare module 'three-vanta';
declare module 'vanta/dist/vanta.net.min' {
  const NET: (options: Record<string, unknown>) => unknown;
  export default NET;
}
