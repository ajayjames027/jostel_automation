#!/usr/bin/env bash
# =========================================================================
# JosTEL Moodle Bare-Metal Machine Restore Helper (Linux / Ubuntu / Docker)
# St. Joseph's College (Autonomous), Tiruchirappalli
# =========================================================================

set -e

echo "========================================================================="
echo "   JosTEL Moodle Bare-Metal Machine Restore Helper (Linux / Ubuntu)     "
echo "========================================================================="
echo ""

read -p "Enter Database Host [default: 127.0.0.1]: " DB_HOST
DB_HOST=${DB_HOST:-127.0.0.1}

read -p "Enter Database User [default: root]: " DB_USER
DB_USER=${DB_USER:-root}

read -s -p "Enter Database Password (leave blank if none): " DB_PASS
echo ""

read -p "Enter Target Database Name [default: moodle]: " DB_NAME
DB_NAME=${DB_NAME:-moodle}

read -p "Enter Path to Moodle SQL dump (.sql or .sql.gz): " SQL_FILE
if [ ! -f "$SQL_FILE" ]; then
    echo "[!] File not found: $SQL_FILE"
    exit 1
fi

# Build MySQL auth flags
PASS_PARAM=""
if [ -n "$DB_PASS" ]; then
    PASS_PARAM="-p$DB_PASS"
fi

echo ""
echo "[1/3] Creating Database '$DB_NAME' with utf8mb4_unicode_ci..."
mysql -h "$DB_HOST" -u "$DB_USER" $PASS_PARAM -e "CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
echo "[OK] Database ready."

echo ""
echo "[2/3] Importing SQL dump into '$DB_NAME'..."
if [[ "$SQL_FILE" == *.gz ]]; then
    zcat "$SQL_FILE" | mysql -h "$DB_HOST" -u "$DB_USER" $PASS_PARAM "$DB_NAME"
else
    mysql -h "$DB_HOST" -u "$DB_USER" $PASS_PARAM "$DB_NAME" < "$SQL_FILE"
fi
echo "[OK] Database import complete!"

echo ""
echo "========================================================================="
echo "[3/3] Next Steps for Full Server Setup:"
echo "========================================================================="
echo "1. Extract moodledata files to your dataroot (e.g. /var/moodledata):"
echo "   sudo chown -R www-data:www-data /var/moodledata"
echo "   sudo chmod -R 777 /var/moodledata"
echo ""
echo "2. Update config.php with your new wwwroot and dataroot:"
echo "   \$CFG->wwwroot  = 'http://your-server-ip/moodle';"
echo "   \$CFG->dataroot = '/var/moodledata';"
echo ""
echo "3. Run domain replacement CLI:"
echo "   sudo -u www-data php /var/www/html/moodle/admin/cli/replace.php \\"
echo "       --search=https://service.sjctni.edu/jostel/moodle \\"
echo "       --replace=http://your-server-ip/moodle"
echo ""
echo "4. Purge caches:"
echo "   sudo -u www-data php /var/www/html/moodle/admin/cli/purge_caches.php"
echo "========================================================================="
echo "[SUCCESS] Restore finished successfully!"
