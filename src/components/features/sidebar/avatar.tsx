interface AvatarProps {
  src: string;
}

export function Avatar({ src }: AvatarProps) {
  const { t } = useTranslation("openhands");
  return (
    <img src={src} alt="user avatar" className="w-full h-full rounded-full" />
  );
}
