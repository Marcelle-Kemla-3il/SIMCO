import argparse
import os
import numpy as np
import cv2
import matplotlib.pyplot as plt

def ensure_gray(img):
    if img.ndim == 2:
        return img
    elif img.ndim == 3 and img.shape[2] == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    elif img.ndim == 3 and img.shape[2] == 4:
        return cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
    else:
        raise ValueError("Unsupported image format with shape: {}".format(img.shape))

def load_gray(path):
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    return ensure_gray(img)

def save_gray(path, img_gray):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cv2.imwrite(path, img_gray)

def show_row(title, images, cmap="gray", save_path=None):
    n = len(images)
    plt.figure(figsize=(4 * n, 4))
    for i, (name, im) in enumerate(images, start=1):
        plt.subplot(1, n, i)
        plt.imshow(im, cmap=cmap)
        plt.title(name)
        plt.axis("off")
    plt.suptitle(title)
    plt.tight_layout()
    if save_path is not None:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=160)
    plt.show()

def add_gaussian_noise(img, sigma=15.0, seed=0):
    rng = np.random.default_rng(seed)
    noise = rng.normal(0.0, sigma, img.shape).astype(np.float32)
    x = img.astype(np.float32) + noise
    x = np.clip(x, 0, 255).astype(np.uint8)
    return x

def kernel_uniform_3x3():
    return (np.ones((3, 3), dtype=np.float32) / 9.0)

def kernel_nonuniform_3x3():
    k = np.array([[1, 2, 1],
                  [2, 4, 2],
                  [1, 2, 1]], dtype=np.float32)
    return k / 16.0

def kernel_dimension_3x3():
    return np.array([0])

def kernel_laplacian_3x3():
    return np.array([[0, -1, 0],
                     [-1, 4, -1],
                     [0, -1, 0]], dtype=np.float32)

def apply_filter2d(img_gray, kernel):
    return cv2.filter2D(img_gray, ddepth=-1, kernel=kernel)

def apply_gaussian(img_gray, ksize, sigma):
    return cv2.GaussianBlur(img_gray, (ksize, ksize), sigmaX=sigma, sigmaY=sigma)


def normalize_to_uint8(img_float):
    x = img_float.astype(np.float32)N
    mn, mx = float(np.min(x)), float(np.max(x))
    if mx - mn < 1e-9:
        return np.zeros_like(x, dtype=np.uint8)
    y = (x - mn) * (255.0 / (mx - mn))
    return y.clip(0, 255).astype(np.uint8)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--img", type=str, required=True, help="Chemin vers une image (sera convertie en niveaux de gris)")
    p.add_argument("--out_dir", type=str, default="tp5_out")
    p.add_argument("--noise_sigma", type=float, default=18.0)
    args = p.parse_args()

    out = args.out_dir
    os.makedirs(out, exist_ok=True)

    img = load_gray(args.img)

    # -------------------------
    # EX1: Convolution uniforme 3x3
    # -------------------------
    k_u = kernel_uniform_3x3()
    img_u = apply_filter2d(img, k_u)
    show_row(
        "Ex1 - Uniform averaging 3x3",
        [("Original", img), ("Filtered (mean 3x3)", img_u)],
        save_path=os.path.join(out, "ex1_uniform_mean.png"),
    )

    # -------------------------
    # EX2: Mean filter + bruit (démonstration noise reduction)
    # (Pour textures / edges, tu peux tester plusieurs images différentes)
    # -------------------------
    img_noisy = add_gaussian_noise(img, sigma=args.noise_sigma, seed=1)
    img_noisy_u = apply_filter2d(img_noisy, k_u)
    show_row(
        "Ex2 - Noise reduction (mean 3x3)",
        [("Original", img), ("Noisy", img_noisy), ("Noisy + mean3x3", img_noisy_u)],
        save_path=os.path.join(out, "ex2_noise_mean.png"),
    )

    # Variation taille filtre (relation size ↔ smoothing)
    k5 = np.ones((5, 5), dtype=np.float32) / 25.0
    k9 = np.ones((9, 9), dtype=np.float32) / 81.0
    img_noisy_m5 = apply_filter2d(img_noisy, k5)
    img_noisy_m9 = apply_filter2d(img_noisy, k9)
    show_row(
        "Ex2 - Effect of filter size (mean 3x3 vs 5x5 vs 9x9)",
        [("Noisy", img_noisy), ("Mean 3x3", img_noisy_u), ("Mean 5x5", img_noisy_m5), ("Mean 9x9", img_noisy_m9)],
        save_path=os.path.join(out, "ex2_filter_size.png"),
    )

    # -------------------------
    # EX3: Non-uniform averaging (approx Gaussian)
    # -------------------------
    k_nu = kernel_nonuniform_3x3()
    img_nu = apply_filter2d(img, k_nu)
    show_row(
        "Ex3 - Non-uniform (1 2 1; 2 4 2; 1 2 1)/16 vs uniform mean",
        [("Original", img), ("Uniform mean 3x3", img_u), ("Non-uniform /16", img_nu)],
        save_path=os.path.join(out, "ex3_nonuniform_vs_uniform.png"),
    )

    # -------------------------
    # EX4: Custom kernel (ex: sharpening / edge enhancement)
    # Tu peux modifier les coeffs pour tester d'autres effets
    # -------------------------
    k_custom = np.array([[0, -1, 0],
                         [-1, 5, -1],
                         [0, -1, 0]], dtype=np.float32)
    img_custom = apply_filter2d(img, k_custom)
    show_row(
        "Ex4 - Custom filter (sharpen kernel)",
        [("Original", img), ("Custom filtered", img_custom)],
        save_path=os.path.join(out, "ex4_custom.png"),
    )

    # -------------------------
    # EX5: Gaussian filtering (scale analysis)
    # -------------------------
    g1 = apply_gaussian(img, ksize=5, sigma=1.0)
    g2 = apply_gaussian(img, ksize=11, sigma=2.5)
    g3 = apply_gaussian(img, ksize=21, sigma=5.0)
    show_row(
        "Ex5 - Gaussian blur (sigma as scale)",
        [("Original", img), ("Gaussian k=5 σ=1.0", g1), ("Gaussian k=11 σ=2.5", g2), ("Gaussian k=21 σ=5.0", g3)],
        save_path=os.path.join(out, "ex5_gaussian_scales.png"),
    )

    # -------------------------
    # EX6: Laplacian filter (2nd derivative)
    # (Affichage souvent mieux en normalisant car valeurs signées)
    # -------------------------
    k_lap = kernel_laplacian_3x3()
    lap = cv2.filter2D(img.astype(np.float32), ddepth=cv2.CV_32F, kernel=k_lap)
    lap_vis = normalize_to_uint8(np.abs(lap))
    show_row(
        "Ex6 - Laplacian response (abs + normalized)",
        [("Original", img), ("|Laplacian| (normalized)", lap_vis)],
        save_path=os.path.join(out, "ex6_laplacian.png"),
    )

    # -------------------------
    # EX7: Practical pipeline (smoothing -> edge enhancing)
    # Ici : Gaussian puis Laplacian (comme guideline)
    # -------------------------
    smooth = apply_gaussian(img, ksize=11, sigma=2.0)
    lap_smooth = cv2.filter2D(smooth.astype(np.float32), ddepth=cv2.CV_32F, kernel=k_lap)
    lap_smooth_vis = normalize_to_uint8(np.abs(lap_smooth))

    show_row(
        "Ex7 - Pipeline: original -> smoothing (Gaussian) -> Laplacian",
        [("Original", img), ("Gaussian (k=11, σ=2.0)", smooth), ("|Laplacian| after smoothing", lap_smooth_vis)],
        save_path=os.path.join(out, "ex7_pipeline.png"),
    )

    print("[OK] Résultats enregistrés dans:", out)


if __name__ == "__main__":
    main()
