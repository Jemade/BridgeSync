# Interface decisions

The interface is deliberately quiet: solid navy navigation, white work surfaces, muted borders and one dark teal action colour. It uses system fonts, regular spacing and a small Lucide icon set. The hand-coded SVG bridge mark has no effects or embedded bitmap.

No gradients, glow, floating decoration, generated illustrations, invented performance increases, animated counters or empty promotional charts are used. Colour communicates state; every coloured state also has a text label. Metrics are queried from the workspace database.

Primary actions appear beside the screen title. Tables prioritise order references, customer, amount and delivery status. Opening an order reveals its job attempts instead of hiding failure behind a generic indicator. Payment errors identify the affected CSV rows. Forms retain user input when validation fails.

Native dialogs provide modal focus and Escape behaviour. Inputs have visible labels. Navigation uses buttons with accessible names and current-page state. Responsive navigation switches to a drawer; wide tables scroll within their own region. Browser tests verify the main workflow and mobile page width.

Screenshots under screenshots/ are actual rendered product views, not image-generated interface promises. The initial concept images were visual exploration; the implemented interface and its real behaviour are the source of truth.
