import re
import xml.etree.ElementTree as ET

def draw_svg_background(ax, svg_path, color="black", alpha=0.15, linewidth=2):
    tree = ET.parse(svg_path)
    root = tree.getroot()

    ns = {"svg": "http://www.w3.org/2000/svg"}
    paths = root.findall(".//svg:path", ns) or root.findall(".//path")

    number_pattern = re.compile(r"-?\d+(?:\.\d+)?")

    for p in paths:
        d = p.attrib.get("d", "")
        nums = [float(x) for x in number_pattern.findall(d)]

        if len(nums) < 4:
            continue

        xs = nums[0::2]
        ys = nums[1::2]

        ax.plot(xs, ys, color=color, alpha=alpha, linewidth=linewidth, zorder=0)