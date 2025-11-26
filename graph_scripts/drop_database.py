#!/usr/bin/env python

from database import driver, drop_all_data

if __name__ == "__main__":
    print("Dropping all data from the database...")
    drop_all_data(driver)
    print("Done!")
    driver.close()
