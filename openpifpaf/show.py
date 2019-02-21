from contextlib import contextmanager
import numpy as np
from PIL import Image

try:
    import matplotlib
    import matplotlib.pyplot as plt
except ImportError:
    matplotlib = None
    plt = None


COCO_PERSON_SKELETON = [
    [16, 14], [14, 12], [17, 15], [15, 13], [12, 13], [6, 12], [7, 13],
    [6, 7], [6, 8], [7, 9], [8, 10], [9, 11], [2, 3], [1, 2], [1, 3],
    [2, 4], [3, 5], [4, 6], [5, 7]]


@contextmanager
def canvas(fig_file=None, show=True, **kwargs):
    if 'figsize' not in kwargs:
        # kwargs['figsize'] = (15, 8)
        kwargs['figsize'] = (10, 6)
    fig, ax = plt.subplots(**kwargs)

    yield ax

    fig.set_tight_layout(True)
    if fig_file:
        fig.savefig(fig_file, dpi=200)  # , bbox_inches='tight')
    if show:
        fig.show()
    plt.close(fig)


@contextmanager
def image_canvas(image, fig_file=None, show=True, dpi_factor=1.0, fig_width=10.0, **kwargs):
    if 'figsize' not in kwargs:
        kwargs['figsize'] = (fig_width, fig_width * image.shape[0] / image.shape[1])

    fig = plt.figure(**kwargs)
    ax = plt.Axes(fig, [0.0, 0.0, 1.0, 1.0])
    ax.set_axis_off()
    ax.set_xlim(0, image.shape[1])
    ax.set_ylim(image.shape[0], 0)
    fig.add_axes(ax)
    ax.imshow(image)

    yield ax

    if fig_file:
        fig.savefig(fig_file, dpi=image.shape[1] / kwargs['figsize'][0] * dpi_factor)
    if show:
        fig.show()
    plt.close(fig)


def load_image(path, scale=1.0):
    with open(path, 'rb') as f:
        image = Image.open(f).convert('RGB')
        image = np.asarray(image) * scale / 255.0
        return image


def keypoints(ax, keypoint_sets,
              skeleton=COCO_PERSON_SKELETON, color=None, xy_scale=1.0,
              highlight=None, show_box=True,
              highlight_invisible=False, linewidth=2, markersize=3,
              scores=None, color_connections=False):
    if keypoint_sets is None:
        return

    for i, kps in enumerate(np.asarray(keypoint_sets)):
        assert kps.shape[1] == 3
        c = color
        x = kps[:, 0] * xy_scale
        y = kps[:, 1] * xy_scale
        v = kps[:, 2]
        if not np.any(v > 0):
            continue
        if skeleton is not None:
            for ci, connection in enumerate(np.array(skeleton) - 1):
                if color_connections:
                    c = matplotlib.cm.get_cmap('tab20')(ci / len(skeleton))
                if np.all(v[connection] > 0):
                    l, = ax.plot(x[connection], y[connection],
                                 linewidth=linewidth, color=c,
                                 linestyle='dashed', dash_capstyle='round')
                    if c is None:
                        c = l.get_color()
                if np.all(v[connection] > 1):
                    ax.plot(x[connection], y[connection],
                            linewidth=linewidth, color=c, solid_capstyle='round')
            if color_connections:
                c = color if color is not None else 'white'

        # highlight invisible keypoints
        inv_c = 'k' if highlight_invisible else c

        ax.plot(x[v > 0], y[v > 0], 'o', markersize=markersize,
                markerfacecolor=c, markeredgecolor=inv_c, markeredgewidth=2)
        ax.plot(x[v > 1], y[v > 1], 'o', markersize=markersize,
                markerfacecolor=c, markeredgecolor=c, markeredgewidth=2)

        if highlight is not None:
            v_highlight = v[highlight]
            ax.plot(x[highlight][v_highlight > 0], y[highlight][v_highlight > 0],
                    'o', markersize=markersize*2,
                    markerfacecolor=c, markeredgecolor=c, markeredgewidth=2)

        if show_box:
            # keypoint bounding box
            x1, x2 = np.min(x[v > 0]), np.max(x[v > 0])
            y1, y2 = np.min(y[v > 0]), np.max(y[v > 0])
            if x2 - x1 < 5.0:
                x1 -= 2.0
                x2 += 2.0
            if y2 - y1 < 5.0:
                y1 -= 2.0
                y2 += 2.0
            ax.add_patch(
                matplotlib.patches.Rectangle(
                    (x1, y1), x2 - x1, y2 - y1, fill=False, color=c))

            if scores is not None:
                score = scores[i]
                ax.text(x1, y1, '{:.4f}'.format(score), fontsize=8)


def quiver(ax, vector_field, intensity_field=None, step=1, threshold=0.5,
           xy_scale=1.0, uv_is_offset=False,
           reg_uncertainty=None, **kwargs):
    x, y, u, v, c, r = [], [], [], [], [], []
    for j in range(0, vector_field.shape[1], step):
        for i in range(0, vector_field.shape[2], step):
            if intensity_field is not None and intensity_field[j, i] < threshold:
                continue
            x.append(i * xy_scale)
            y.append(j * xy_scale)
            u.append(vector_field[0, j, i] * xy_scale)
            v.append(vector_field[1, j, i] * xy_scale)
            c.append(intensity_field[j, i] if intensity_field is not None else 1.0)
            r.append(reg_uncertainty[j, i] * xy_scale if reg_uncertainty is not None else None)
    x = np.array(x)
    y = np.array(y)
    u = np.array(u)
    v = np.array(v)
    c = np.array(c)
    r = np.array(r)
    s = np.argsort(c)
    if uv_is_offset:
        u -= x
        v -= y

    for xx, yy, uu, vv, cc, rr in zip(x, y, u, v, c, r):
        if not rr:
            continue
        circle = matplotlib.patches.Circle(
            (xx + uu, yy + vv), rr / 2.0, zorder=10, linewidth=1, alpha=0.5)
        ax.add_artist(circle)

    return ax.quiver(x[s], y[s], u[s], v[s], c[s],
                     angles='xy', scale_units='xy', scale=1, zOrder=10, **kwargs)


def arrows(ax, fourd, xy_scale=1.0, threshold=0.0, **kwargs):
    mask = np.min(fourd[:, 2], axis=0) >= threshold
    fourd = fourd[:, :, mask]
    (x1, y1), (x2, y2) = fourd[:, :2, :] * xy_scale
    c = np.min(fourd[:, 2], axis=0)
    s = np.argsort(c)
    return ax.quiver(x1[s], y1[s], (x2 - x1)[s], (y2 - y1)[s], c[s],
                     angles='xy', scale_units='xy', scale=1, zOrder=10, **kwargs)


def white_screen(ax, alpha=0.9):
    ax.add_patch(
        plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes, alpha=alpha,
                      facecolor='white')
    )