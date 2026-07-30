library(readr)
library(dplyr)
library(ggplot2)
library(stringr)
library(jsonlite)
library(purrr)

root <- getwd()
zip_path <- file.path(root, "Elite Prospects Hockey Stats & Player Data.zip")

extract_csv <- function(path, archive_path) {
  temp_dir <- tempfile("nhl_data")
  dir.create(temp_dir)
  unzip(zip_path, files = archive_path, exdir = temp_dir)
  read_csv(file.path(temp_dir, basename(archive_path)), show_col_types = FALSE)
}

player_dim <- extract_csv(zip_path, "player_dim.csv")
player_stats <- extract_csv(zip_path, "player_stats.csv")

position_lookup <- player_stats %>%
  filter(!is.na(PRIMARY_POS) & PRIMARY_POS != "") %>%
  mutate(PRIMARY_POS = str_to_upper(PRIMARY_POS)) %>%
  group_by(PLAYER_ID) %>%
  summarise(PRIMARY_POS = first(PRIMARY_POS), .groups = "drop")

players <- player_dim %>%
  distinct(PLAYER_ID, .keep_all = TRUE) %>%
  left_join(position_lookup, by = "PLAYER_ID") %>%
  mutate(
    height_cm = as.numeric(HEIGHT_CM)
  ) %>%
  filter(!is.na(height_cm), !is.na(PRIMARY_POS), PRIMARY_POS != "")

players <- players %>%
  mutate(
    position_group = case_when(
      PRIMARY_POS %in% c("C", "LW", "RW", "W", "F", "L", "R", "LF", "RF") ~ "Forward",
      PRIMARY_POS %in% c("D", "LD", "RD", "DD") ~ "Defense",
      PRIMARY_POS %in% c("G", "GK", "GOALIE") ~ "Goalie",
      TRUE ~ "Other"
    )
  )

summary_tbl <- players %>%
  group_by(position_group) %>%
  summarise(
    count = n(),
    mean_height = round(mean(height_cm, na.rm = TRUE), 1),
    median_height = round(median(height_cm, na.rm = TRUE), 1),
    sd_height = round(sd(height_cm, na.rm = TRUE), 1),
    .groups = "drop"
  )

hist_data <- data.frame(height_cm = players$height_cm)

hist_plot <- ggplot(hist_data, aes(x = height_cm)) +
  geom_histogram(binwidth = 5, fill = "#4fd1c5", color = "#071b2f", alpha = 0.95, linewidth = 0.5) +
  geom_density(aes(y = after_stat(count) * 5), color = "#ffd166", linewidth = 1.1, alpha = 0.7) +
  labs(
    title = "Distribution of NHL player heights",
    x = "Height (cm)",
    y = "Count"
  ) +
  xlim(150, 210) +
  theme_minimal(base_size = 16) +
  theme(
    plot.title = element_text(size = 18, face = "bold", color = "#f8fbff"),
    axis.title = element_text(color = "#f8fbff"),
    axis.text = element_text(color = "#f8fbff"),
    panel.background = element_rect(fill = "#071b2f", color = NA),
    plot.background = element_rect(fill = "#071b2f", color = NA),
    panel.grid.major = element_line(color = "#214a67"),
    panel.grid.minor = element_blank()
  )

box_plot <- ggplot(players, aes(x = position_group, y = height_cm, fill = position_group)) +
  geom_boxplot(alpha = 0.9, outlier.alpha = 0.4, width = 0.6) +
  geom_jitter(width = 0.12, alpha = 0.05, color = "#f8fbff") +
  scale_fill_manual(values = c("Defense" = "#4fd1c5", "Forward" = "#70b7ff", "Goalie" = "#ff6b6b", "Other" = "#f7d774")) +
  labs(
    title = "Height by position group",
    x = "Position group",
    y = "Height (cm)"
  ) +
  ylim(150, 210) +
  theme_minimal(base_size = 16) +
  theme(
    plot.title = element_text(size = 18, face = "bold", color = "#f8fbff"),
    axis.title = element_text(color = "#f8fbff"),
    axis.text = element_text(color = "#f8fbff"),
    panel.background = element_rect(fill = "#071b2f", color = NA),
    plot.background = element_rect(fill = "#071b2f", color = NA),
    panel.grid.major = element_line(color = "#214a67"),
    panel.grid.minor = element_blank(),
    legend.position = "none"
  )

# Export images
png("assets/histogram.png", width = 1000, height = 650, bg = "#071b2f")
print(hist_plot)
dev.off()

png("assets/boxplot.png", width = 1000, height = 650, bg = "#071b2f")
print(box_plot)
dev.off()

# Save summary data
write_json(summary_tbl, "nhl_player_data.json", pretty = TRUE, auto_unbox = TRUE)

cat("Generated charts and summary data.\n")
print(summary_tbl)
