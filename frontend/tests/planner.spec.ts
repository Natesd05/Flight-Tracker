import { test, expect } from "@playwright/test";

test("student planning flow persists classes, preferences, searches and comparisons", async ({
  page,
  request,
}, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const originalPrefs = await (await request.get("/api/preferences")).json();
  const originalSchedule = await (await request.get("/api/schedule")).json();
  const originalSaved = await (await request.get("/api/saved")).json();
  const className = `Smoke seminar ${testInfo.project.name}`;
  try {
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: "Where to after class?" }),
    ).toBeVisible();
    await expect(page.getByText("Demo flight data")).toBeVisible();
    await page
      .getByRole("button", { name: "My schedule", exact: true })
      .click();
    await page.getByLabel("Class name", { exact: true }).fill(className);
    await page.getByLabel("Day of week").selectOption("4");
    await page.getByLabel("Class starts").fill("10:00");
    await page.getByLabel("Class ends").fill("12:00");
    await page.getByRole("button", { name: "Add class", exact: true }).click();
    await expect(page.getByRole("status")).toContainText("Class added");
    await page.getByRole("button", { name: new RegExp(className) }).click();
    await page.getByLabel("Class ends").fill("11:30");
    await page
      .getByRole("button", { name: "Update class", exact: true })
      .click();
    await expect(page.getByRole("status")).toContainText("Class updated");
    await page
      .getByRole("button", { name: "Preferences", exact: true })
      .click();
    await page.getByLabel("Total budget (USD)", { exact: true }).fill("650");
    await page
      .getByRole("button", { name: "Save preferences", exact: true })
      .click();
    await expect(page.getByRole("status")).toContainText("Preferences saved");
    await page
      .getByRole("button", { name: "Find flights", exact: true })
      .click();
    await page.getByLabel("Depart from", { exact: true }).fill("2026-09-11");
    await page.getByLabel("Depart by", { exact: true }).fill("2026-09-11");
    await page.getByLabel("Return from", { exact: true }).fill("2026-09-13");
    await page.getByLabel("Return by", { exact: true }).fill("2026-09-13");
    await page
      .getByRole("button", { name: "Find my flights", exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: "6 flights to consider" }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Why this flight" }).first().click();
    await expect(
      page.getByRole("heading", { name: "The tradeoffs" }),
    ).toBeVisible();
    await expect(
      page.getByText("Each bar shows fit for that factor.", { exact: false }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Why this flight" }).first().click();
    await page
      .getByRole("button", { name: "Save flight", exact: true })
      .first()
      .click();
    await expect(page.getByRole("status")).toContainText("Flight saved");
    await page
      .getByRole("button", { name: "Save flight", exact: true })
      .first()
      .click();
    await expect(
      page.getByRole("button", { name: "Saved", exact: true }),
    ).toHaveCount(2);
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({
      path: `test-results/${testInfo.project.name}-results.png`,
      fullPage: true,
    });
    await page.getByRole("button", { name: /^Saved flights/ }).click();
    await page
      .getByRole("checkbox", { name: /^Compare / })
      .nth(0)
      .check();
    await page
      .getByRole("checkbox", { name: /^Compare / })
      .nth(1)
      .check();
    await expect(
      page.getByRole("heading", { name: "Side-by-side comparison" }),
    ).toBeVisible();
    await expect(page.getByRole("table").getByRole("columnheader")).toHaveCount(
      3,
    );
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({
      path: `test-results/${testInfo.project.name}-comparison.png`,
      fullPage: true,
    });
    await page.reload();
    await page.getByRole("button", { name: /^Saved flights/ }).click();
    await expect(page.getByRole("checkbox", { name: /^Compare / })).toHaveCount(
      originalSaved.length + 2,
    );
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBeTruthy();
    expect(errors).toEqual([]);
  } finally {
    await request.put("/api/preferences", { data: originalPrefs });
    const currentSchedule = await (await request.get("/api/schedule")).json();
    for (const c of currentSchedule.classes)
      if (
        !originalSchedule.classes.some((x: { id: number }) => x.id === c.id) &&
        c.title === className
      )
        await request.delete(`/api/classes/${c.id}`);
    const currentSaved = await (await request.get("/api/saved")).json();
    for (const s of currentSaved)
      if (!originalSaved.some((x: { id: number }) => x.id === s.id))
        await request.delete(`/api/saved/${s.id}`);
  }
});

test("empty results explain hard constraints and responsive layout stays within viewport", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Find my flights" }),
  ).toBeVisible();
  await page.getByLabel("Min days away").fill("0");
  await page.getByLabel("Max days away").fill("0.5");
  await page.getByRole("button", { name: "Find my flights" }).click();
  await expect(
    page.getByRole("heading", { name: "No flights meet all your constraints" }),
  ).toBeVisible();
  await expect(
    page.getByText("Widen the allowed door-to-door trip duration."),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
});

test("comparison selection is capped at three and sorting/filtering work", async ({
  page,
  request,
}) => {
  const created: number[] = [];
  const response = await request.post("/api/searches", {
    data: {
      origin: "ORD",
      destination: "LAX",
      departure_from: "2026-09-11",
      departure_to: "2026-09-11",
      return_from: "2026-09-13",
      return_to: "2026-09-13",
      hard_budget: false,
    },
  });
  const result = await response.json();
  try {
    for (const option of result.results.slice(0, 4)) {
      const saved = await (
        await request.post("/api/saved", {
          data: { search_id: result.id, itinerary_id: option.itinerary.id },
        })
      ).json();
      created.push(saved.id);
    }
    await page.goto("/");
    await page.getByRole("button", { name: /^Saved flights/ }).click();
    const boxes = page.getByRole("checkbox", { name: /^Compare / });
    await boxes.nth(0).check();
    await boxes.nth(1).check();
    await boxes.nth(2).check();
    await expect(boxes.nth(3)).toBeDisabled();
    await expect(page.getByRole("table").getByRole("columnheader")).toHaveCount(
      4,
    );
    await boxes.nth(0).uncheck();
    await expect(boxes.nth(3)).toBeEnabled();
    await page
      .getByRole("button", { name: "Find flights", exact: true })
      .click();
    await page
      .getByRole("button", { name: "Find my flights", exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: /flights to consider/ }),
    ).toBeVisible();
    await page.getByLabel("Sort flights").selectOption("cost");
    const totals = await page.locator(".price > strong").allTextContents();
    const values = totals.map((x) => Number(x.replace(/[^0-9.]/g, "")));
    expect(values).toEqual([...values].sort((a, b) => a - b));
    await page.getByLabel("Filter maximum total cost").fill("1");
    await expect(
      page.getByRole("heading", { name: "No matches for these filters" }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Clear result filters" }).click();
    await expect(page.locator(".flight-card").first()).toBeVisible();
  } finally {
    for (const id of created) await request.delete(`/api/saved/${id}`);
  }
});
