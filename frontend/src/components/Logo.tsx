import React from 'react'

/** The Scholar mark (public/logo.svg) — also the favicon. */
export const Logo: React.FC<{ size: number; style?: React.CSSProperties }> = ({ size, style }) => (
  <img src="/logo.svg" alt="Scholar" width={size} height={size} style={{ display: 'block', flexShrink: 0, ...style }} />
)
