/* ============================================================
   SIMPLE CANVAS CHART
============================================================ */

function drawTrendChart(history) {

    const canvas =
        document.getElementById(
            "trendChart"
        );

    if (!canvas || !history) {
        return;
    }

    const ctx =
        canvas.getContext("2d");

    const width =
        canvas.clientWidth;

    const height = 300;

    canvas.width =
        width * window.devicePixelRatio;

    canvas.height =
        height * window.devicePixelRatio;

    ctx.scale(
        window.devicePixelRatio,
        window.devicePixelRatio
    );

    const values =
        history.values;

    if (!values || values.length < 2) {
        return;
    }

    const min =
        Math.min(...values);

    const max =
        Math.max(...values);

    const padding = 30;

    function x(i) {

        return padding +
            i *
            (
                (width - padding * 2) /
                (values.length - 1)
            );

    }

    function y(value) {

        return height -
            padding -
            (
                (value - min) /
                (max - min || 1)
            )
            *
            (height - padding * 2);

    }

    ctx.clearRect(
        0,
        0,
        width,
        height
    );


    /*
       Grid
    */

    ctx.strokeStyle =
        "#243b4a";

    ctx.lineWidth = 1;

    for (
        let i = 0;
        i < 5;
        i++
    ) {

        const yy =
            padding +
            i *
            (
                (height - padding * 2) /
                4
            );

        ctx.beginPath();

        ctx.moveTo(
            padding,
            yy
        );

        ctx.lineTo(
            width - padding,
            yy
        );

        ctx.stroke();

    }


    /*
       Line
    */

    ctx.strokeStyle =
        "#72b6ff";

    ctx.lineWidth = 2;

    ctx.beginPath();

    values.forEach(
        (value, i) => {

            const xx = x(i);
            const yy = y(value);

            if (i === 0) {

                ctx.moveTo(
                    xx,
                    yy
                );

            } else {

                ctx.lineTo(
                    xx,
                    yy
                );

            }

        }
    );

    ctx.stroke();
}