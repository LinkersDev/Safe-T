import { cn } from '../../core/utils/cn'

type LogoAvatarProps = {
  src: string
  alt: string
  className?: string
}

/**
 * LogoAvatar renders a circular, glassmorphic logo container.
 * Modern tech-forward design with subtle shadow and glassmorphic background.
 *
 * Features:
 * - 100px circle (w-24 h-24)
 * - Glassmorphic background with backdrop blur
 * - Centered image with proper aspect ratio
 * - Subtle shadow and border effects
 * - Smooth fade-in animation on mount
 */
export function LogoAvatar({ src, alt, className }: LogoAvatarProps) {
  return (
    <div
      className={cn(
        'w-24 h-24 rounded-full',
        'glassmorphic',
        'flex items-center justify-center',
        'shadow-lg',
        'animate-fade-in',
        className,
      )}
    >
      <img
        src={src}
        alt={alt}
        className="w-20 h-20 object-cover"
      />
    </div>
  )
}
