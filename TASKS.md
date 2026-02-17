# Tasks

0. Split up program into different files for more convenience.
1. Fix alignment; labels are too close to previous controls.
2. In History, auto-update on any filter interaction (no Apply button).
3. Fix History "From" filter (currently not working).
4. Redesign Expenses layout:
   - More area for setup controls
   - Less height for grid
   - Grid should be scrollable (vertical scrollbar)
5. Analytics redesign with selectable views:
   - Select range:
     - If < 2 full months: optional charts by day, by week (Mon start), by every 7 days from range start, by month
     - If >= 2 full months: optional charts by week (Mon start), by every 7 days from range start, by month
   - Add pie chart for selected range with configurable grouping:
     - Store, Person, Category, Subcategory (nested by category), and possibly others
   - When clicking a day/week/month bar in the range, show additional charts scoped to that bucket.
