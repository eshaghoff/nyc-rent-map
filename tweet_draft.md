# Tweet Thread Draft — NYC Rent Heat Map

## Tweet 1 (Hook + GIF)
I mapped every 1BR rental on StreetEasy to see what NYC rent actually looks like.

43,237 market-rate listings. One interactive heat map.

🔗 eshaghoff.github.io/nyc-rent-map

[Attach: nyc-rent-heatmap-demo.gif]

## Tweet 2 (Key findings)
Some numbers that jumped out:

• Lower Manhattan median: $4,600
• North Brooklyn: $3,900
• W. Queens (LIC/Astoria): $3,550
• Upper Manhattan: $2,500
• South Brooklyn: $2,200
• Staten Island: $1,775

The gap between the most and least expensive regions is 2.6x.

## Tweet 3 (Interesting observations)
The most interesting thing is how hyperlocal rent is.

Mott Haven in the South Bronx has a $2,888 median — driven almost entirely by new luxury construction. The rest of the Bronx? $2,169.

One neighborhood of new buildings moved an entire sub-borough's median by $700.

## Tweet 4 (How it was built)
How I built it:
- Scraped StreetEasy for active + recently rented 1BR listings
- Filtered out rent-stabilized units using spatial median analysis
- Plotted on an adaptive grid (finer in Manhattan, coarser in outer boroughs)
- Color gradient from green ($1,800) → red ($8,000+)

All open source: github.com/eshaghoff/nyc-rent-map

## Tweet 5 (CTA)
The map updates quarterly with fresh data. You can filter by 9 regions, toggle subway stations, and see neighborhood-level detail.

If you're apartment hunting in NYC, this might save you some time.

🔗 eshaghoff.github.io/nyc-rent-map
