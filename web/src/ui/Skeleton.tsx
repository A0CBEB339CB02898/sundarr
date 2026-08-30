import React from 'react'

type SkeletonProps = {
  width?: number | string
  height?: number | string
  radius?: number | string
  className?: string
  style?: React.CSSProperties
}

/**
 * Skeleton · docs/11-前端设计系统.md §6.13
 * 提供 width / height / radius 三个便捷 prop；否则靠外层控制尺寸。
 */
export function Skeleton({ width, height, radius, className, style }: SkeletonProps) {
  const cls = className ? `ui-skeleton ${className}` : 'ui-skeleton'
  const merged: React.CSSProperties = {
    width,
    height,
    borderRadius: radius,
    ...style,
  }
  return <span className={cls} style={merged} aria-hidden="true" />
}
