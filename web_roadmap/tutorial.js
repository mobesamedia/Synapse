/* Editable first-use example. Never replaces saved maps.
   Fixed card palettes have explicit contrasting ink; free text follows the canvas theme. */
window.createRoadmapTutorial = function (t) {
    const map = {
    "id": "roadmap-tutorial",
    "name": "FreeMap Tutorial",
    "objects": [
        {
            "fill": "#ffffff",
            "fontSize": 48,
            "h": 100,
            "html": "<b>Your ideas, without a template</b>",
            "id": "tutorial-title",
            "kind": "text",
            "rotation": 0,
            "shape": "rect",
            "stroke": "#536779",
            "w": 1000,
            "x": 0,
            "y": 0
        },
        {
            "fill": "#ffffff",
            "fontSize": 23,
            "h": 76,
            "html": "A canvas for connections, explanations and plans. Enlarge the view and explore.",
            "id": "tutorial-intro",
            "kind": "text",
            "rotation": 0,
            "shape": "rect",
            "stroke": "#536779",
            "w": 870,
            "x": 0,
            "y": 106
        },
        {
            "fill": "#ffffff",
            "fontSize": 23,
            "h": 58,
            "html": "<b>01 · Make space for ideas</b>",
            "id": "tutorial-section-one",
            "kind": "text",
            "rotation": 0,
            "shape": "rect",
            "stroke": "#536779",
            "w": 390,
            "x": 0,
            "y": 222
        },
        {
            "fill": "#ffffff",
            "fontSize": 23,
            "h": 58,
            "html": "<b>02 · Explain a connection</b>",
            "id": "tutorial-section-two",
            "kind": "text",
            "rotation": 0,
            "shape": "rect",
            "stroke": "#536779",
            "w": 542,
            "x": 458,
            "y": 222
        },
        {
            "customStyle": true,
            "fill": "#cee0ee",
            "fontSize": 24,
            "h": 158,
            "html": "<span style=\"color:#233b50\"><b>Start with a thought</b><br>Use + for shapes, free text and images. Double-click to write.</span>",
            "id": "tutorial-shapes",
            "kind": "shape",
            "rotation": 0,
            "shape": "rounded",
            "stroke": "#8caec7",
            "w": 390,
            "x": 0,
            "y": 306
        },
        {
            "customStyle": true,
            "fill": "#d9d4ec",
            "fontSize": 24,
            "h": 158,
            "html": "<span style=\"color:#3d3358\"><b>Give it structure</b><br>Drag the blue connection points. Arrows stay attached when you move a shape.</span>",
            "id": "tutorial-connect",
            "kind": "shape",
            "rotation": 0,
            "shape": "rect",
            "stroke": "#aaa0cc",
            "w": 390,
            "x": 0,
            "y": 518
        },
        {
            "customStyle": true,
            "fill": "#ecd9ca",
            "fontSize": 24,
            "h": 158,
            "html": "<span style=\"color:#50392b\"><b>Make it yours</b><br>Select text to style it. Resize, rotate and recolor objects. Try Undo.</span>",
            "id": "tutorial-style",
            "kind": "shape",
            "rotation": 0,
            "shape": "rounded",
            "stroke": "#c4a68e",
            "w": 390,
            "x": 0,
            "y": 730
        },
        {
            "a": {
                "node": "tutorial-shapes",
                "side": "bottom"
            },
            "b": {
                "node": "tutorial-connect",
                "side": "top"
            },
            "dash": "solid",
            "fill": "#ffffff",
            "id": "tutorial-arrow-0",
            "kind": "arrow",
            "label": "Connect",
            "labelSize": 16,
            "route": "rounded",
            "stroke": "#8194a8",
            "tip": "triangle",
            "customStyle": true
        },
        {
            "a": {
                "node": "tutorial-connect",
                "side": "bottom"
            },
            "b": {
                "node": "tutorial-style",
                "side": "top"
            },
            "dash": "solid",
            "fill": "#ffffff",
            "id": "tutorial-arrow-1",
            "kind": "arrow",
            "label": "Experiment",
            "labelSize": 16,
            "route": "curve",
            "stroke": "#8194a8",
            "tip": "open",
            "customStyle": true
        },
        {
            "customStyle": true,
            "fill": "#264b50",
            "fontSize": 27,
            "h": 186,
            "html": "<span style=\"color:#ffffff\"><b>Can I explain it?</b></span>",
            "id": "tutorial-question",
            "kind": "shape",
            "rotation": 0,
            "shape": "diamond",
            "stroke": "#668e93",
            "w": 300,
            "x": 580,
            "y": 294
        },
        {
            "customStyle": true,
            "fill": "#cce1d6",
            "fontSize": 23,
            "h": 154,
            "html": "<span style=\"color:#284c3c\"><b>Yes · Practice</b><br>Recall it without looking.</span>",
            "id": "tutorial-practice",
            "kind": "shape",
            "rotation": 0,
            "shape": "rounded",
            "stroke": "#87b29d",
            "w": 248,
            "x": 458,
            "y": 522
        },
        {
            "customStyle": true,
            "fill": "#eddbc0",
            "fontSize": 23,
            "h": 154,
            "html": "<span style=\"color:#594225\"><b>Not yet · Explore</b><br>Add an example or image.</span>",
            "id": "tutorial-rethink",
            "kind": "shape",
            "rotation": 0,
            "shape": "rounded",
            "stroke": "#c6a472",
            "w": 248,
            "x": 752,
            "y": 522
        },
        {
            "customStyle": true,
            "fill": "#264b50",
            "fontSize": 24,
            "h": 158,
            "html": "<span style=\"color:#ffffff\"><b>Connect it to your learning</b><br>Use Link Card on an object to attach a real Anki card. Keep context beside your ideas.</span>",
            "id": "tutorial-explore",
            "kind": "shape",
            "rotation": 0,
            "shape": "rounded",
            "stroke": "#668e93",
            "w": 542,
            "x": 458,
            "y": 730
        },
        {
            "a": {
                "node": "tutorial-question",
                "side": "left"
            },
            "b": {
                "node": "tutorial-practice",
                "side": "top"
            },
            "dash": "solid",
            "fill": "#ffffff",
            "id": "tutorial-yes",
            "kind": "arrow",
            "label": "Yes",
            "labelSize": 16,
            "route": "straight",
            "stroke": "#699e86",
            "tip": "triangle",
            "customStyle": true
        },
        {
            "a": {
                "node": "tutorial-question",
                "side": "right"
            },
            "b": {
                "node": "tutorial-rethink",
                "side": "top"
            },
            "dash": "solid",
            "fill": "#ffffff",
            "id": "tutorial-notyet",
            "kind": "arrow",
            "label": "Not yet",
            "labelSize": 16,
            "route": "rounded",
            "stroke": "#b18c57",
            "tip": "triangle",
            "customStyle": true
        },
        {
            "a": {
                "node": "tutorial-practice",
                "side": "bottom"
            },
            "b": {
                "node": "tutorial-explore",
                "side": "top"
            },
            "dash": "solid",
            "fill": "#ffffff",
            "id": "tutorial-review",
            "kind": "arrow",
            "label": "",
            "labelSize": 16,
            "route": "rounded",
            "stroke": "#699e86",
            "tip": "triangle",
            "customStyle": true
        },
        {
            "a": {
                "node": "tutorial-rethink",
                "side": "bottom"
            },
            "b": {
                "node": "tutorial-explore",
                "side": "top"
            },
            "dash": "dashed",
            "fill": "#ffffff",
            "id": "tutorial-examples",
            "kind": "arrow",
            "label": "",
            "labelSize": 16,
            "route": "curve",
            "stroke": "#b18c57",
            "tip": "open",
            "customStyle": true
        },
        {
            "customStyle": true,
            "fill": "#e5dbb9",
            "fontSize": 22,
            "h": 152,
            "html": "<span style=\"color:#4b432c\"><b>A note on the side</b><br>Not everything needs an arrow. Move this note anywhere.</span>",
            "id": "tutorial-note",
            "kind": "shape",
            "rotation": -3,
            "shape": "rounded",
            "stroke": "#b8a879",
            "w": 330,
            "x": 0,
            "y": 1018
        },
        {
            "fill": "#ffffff",
            "fontSize": 25,
            "h": 56,
            "html": "<b>03 · Keep exploring</b>",
            "id": "tutorial-free-text",
            "kind": "text",
            "rotation": 0,
            "shape": "rect",
            "stroke": "#536779",
            "w": 542,
            "x": 458,
            "y": 958
        },
        {
            "fill": "#ffffff",
            "fontSize": 21,
            "h": 158,
            "html": "Pan or zoom to explore. Center keeps your zoom; Fit shows everything. Changes save automatically. Export a backup or delete this tutorial from the map menu.",
            "id": "tutorial-footer",
            "kind": "text",
            "rotation": 0,
            "shape": "rect",
            "stroke": "#536779",
            "w": 542,
            "x": 458,
            "y": 1030
        },
        {
            "id": "tutorial-swatch-0",
            "kind": "shape",
            "shape": "circle",
            "x": 918,
            "y": 152,
            "w": 22,
            "h": 22,
            "rotation": 0,
            "fontSize": 20,
            "html": "",
            "fill": "#cee0ee",
            "stroke": "#8caec7",
            "customStyle": true
        },
        {
            "id": "tutorial-swatch-1",
            "kind": "shape",
            "shape": "squircle",
            "x": 948,
            "y": 152,
            "w": 22,
            "h": 22,
            "rotation": 0,
            "fontSize": 20,
            "html": "",
            "fill": "#d9d4ec",
            "stroke": "#aaa0cc",
            "customStyle": true
        },
        {
            "id": "tutorial-swatch-2",
            "kind": "shape",
            "shape": "diamond",
            "x": 978,
            "y": 152,
            "w": 22,
            "h": 22,
            "rotation": 0,
            "fontSize": 20,
            "html": "",
            "fill": "#cce1d6",
            "stroke": "#87b29d",
            "customStyle": true
        }
    ],
    "view": {
        "scale": 0.6,
        "x": 40,
        "y": 40
    },
    "assets": {}
};
    map.name = t('FreeMap Tutorial');
    // Translate plain text while preserving editable formatting and color choices.
    // Translation output remains plain text, never executable markup.
    for (const object of map.objects) {
        if (object.html) {
            const template = document.createElement('template');
            template.innerHTML = object.html;
            const walker = document.createTreeWalker(template.content, NodeFilter.SHOW_TEXT);
            let node;
            while ((node = walker.nextNode())) {
                if (node.nodeValue.trim()) node.nodeValue = t(node.nodeValue);
            }
            object.html = template.innerHTML;
        }
        if (object.label) object.label = t(object.label);
    }
    return map;
};
