import React from "react";
import { LoaderCircle } from "lucide-react";
import { PastedImageUploadAsFileButton } from "./pasted-image-upload-as-file-button";
import { RemoveFileButton } from "./remove-file-button";
import { Spinner } from "#/components/shared/spinner";

interface UploadedImageProps {
  image: File;
  onRemove: () => void;
  isLoading?: boolean;
  showUploadAsFileToggle?: boolean;
  uploadAsFileActive?: boolean;
  onToggleUploadAsFile?: () => void;
}

export function UploadedImage({
  image,
  onRemove,
  isLoading = false,
  showUploadAsFileToggle = false,
  uploadAsFileActive = false,
  onToggleUploadAsFile,
}: UploadedImageProps) {
  const [imageUrl, setImageUrl] = React.useState<string>("");

  React.useEffect(() => {
    // Create object URL for image preview
    const url = URL.createObjectURL(image);
    setImageUrl(url);

    // Cleanup function to revoke object URL
    return () => {
      URL.revokeObjectURL(url);
    };
  }, [image]);

  return (
    <div className="group relative flex h-12.25 w-12.75 min-h-12.25 min-w-12.75 items-center justify-center rounded-lg bg-interactive-hover">
      {isLoading ? (
        <Spinner size="sm" className="w-5 h-5 text-white" />
      ) : (
        imageUrl && (
          <img
            src={imageUrl}
            alt={image.name}
            className="h-full w-full rounded-lg object-cover"
          />
        )
      )}
      <RemoveFileButton onClick={onRemove} />
      {showUploadAsFileToggle && onToggleUploadAsFile && (
        <PastedImageUploadAsFileButton
          active={uploadAsFileActive}
          onToggle={onToggleUploadAsFile}
        />
      )}
    </div>
  );
}
